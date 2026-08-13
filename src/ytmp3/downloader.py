"""Playlist extraction and the download → convert → tag pipeline."""

from __future__ import annotations

import shutil
import threading
from collections.abc import Callable, Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError

from .config import Settings
from .covers import CoverFinder
from .naming import TrackName, build_stem, parse_track, safe_filename
from .tagging import tag_mp3

Event = Callable[[str, dict[str, Any]], None]

# Everything that can go wrong reaching or reading a URL, as one catchable group.
EXTRACTION_ERRORS = (DownloadError, ExtractorError, RuntimeError, OSError)

# YouTube gates its audio formats behind a JavaScript "n challenge". yt-dlp only
# enables deno by default, so offer every runtime we can find, with none of them
# YouTube serves storyboard images and nothing else.
JS_RUNTIMES = ("deno", "node", "bun", "quickjs")


@dataclass(slots=True)
class Entry:
    """A playlist item from flat extraction."""

    index: int
    video_id: str
    url: str
    title: str


@dataclass(slots=True)
class Playlist:
    title: str
    entries: list[Entry]


@dataclass(slots=True)
class TrackResult:
    entry: Entry
    status: str  # downloaded | skipped | failed
    path: Path | None = None
    name: TrackName | None = None
    cover_source: str | None = None
    error: str | None = None


@dataclass(slots=True)
class RunReport:
    playlist: str
    output_dir: Path
    results: list[TrackResult] = field(default_factory=list)

    def of(self, status: str) -> list[TrackResult]:
        return [r for r in self.results if r.status == status]


class Archive:
    """Already-downloaded video ids, so reruns resume."""

    def __init__(self, path: Path | None) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._ids: set[str] = set()
        if path and path.exists():
            self._ids = {
                line.strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }

    def __contains__(self, video_id: str) -> bool:
        with self._lock:
            return video_id in self._ids

    def add(self, video_id: str) -> None:
        if self._path is None:
            return
        with self._lock:
            if video_id in self._ids:
                return
            self._ids.add(video_id)
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(f"{video_id}\n")


class _SilentLogger:
    """Swallow yt-dlp console output; errors still arrive as exceptions."""

    def debug(self, msg: str) -> None: ...
    def info(self, msg: str) -> None: ...
    def warning(self, msg: str) -> None: ...
    def error(self, msg: str) -> None: ...


def available_js_runtimes() -> dict[str, dict[str, Any]]:
    return {name: {} for name in JS_RUNTIMES if shutil.which(name)}


def _base_opts(settings: Settings) -> dict[str, Any]:
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "ignoreerrors": False,
        "retries": 5,
        "fragment_retries": 5,
        "logger": _SilentLogger(),
        "js_runtimes": available_js_runtimes(),
    }
    if settings.cookies_file:
        opts["cookiefile"] = str(settings.cookies_file)
    if settings.cookies_from_browser:
        opts["cookiesfrombrowser"] = (settings.cookies_from_browser,)
    return opts


def _ydl(opts: dict[str, Any]) -> YoutubeDL:
    """yt-dlp types its options as a closed TypedDict; ours is assembled at runtime."""
    return YoutubeDL(cast("Any", opts))


def fetch_playlist(url: str, settings: Settings) -> Playlist:
    """Flat-extract the track list before downloading anything."""
    opts = _base_opts(settings) | {"extract_flat": "in_playlist", "skip_download": True}
    if settings.playlist_items:
        opts["playlist_items"] = settings.playlist_items

    with _ydl(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if info is None:
        raise RuntimeError(f"Nothing could be extracted from {url}")

    raw_entries: Iterable[Mapping[str, Any]]
    if info.get("_type") in {"playlist", "multi_video"}:
        raw_entries = [e for e in (info.get("entries") or []) if e]
        title = info.get("title") or info.get("id") or "playlist"
    else:
        # A single video URL is treated as a one-track playlist.
        raw_entries = [info]
        title = info.get("title") or "video"

    entries: list[Entry] = []
    for position, item in enumerate(raw_entries, start=1):
        video_id = item.get("id") or ""
        url_ = item.get("url") or item.get("webpage_url")
        if not url_ and video_id:
            url_ = f"https://www.youtube.com/watch?v={video_id}"
        if not url_:
            continue
        entries.append(
            Entry(
                index=item.get("playlist_index") or position,
                video_id=video_id,
                url=url_,
                title=item.get("title") or video_id or url_,
            )
        )

    if settings.limit is not None:
        entries = entries[: settings.limit]
    return Playlist(title=title, entries=entries)


class PlaylistDownloader:
    def __init__(self, settings: Settings, on_event: Event | None = None) -> None:
        self.settings = settings
        self._emit = on_event or (lambda _name, _data: None)
        self._archive = Archive(settings.archive)
        self._finder = CoverFinder(size=settings.cover_size) if settings.covers else None

    def close(self) -> None:
        if self._finder is not None:
            self._finder.close()

    def __enter__(self) -> PlaylistDownloader:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def run(self, url: str) -> RunReport:
        playlist = fetch_playlist(url, self.settings)
        self._emit("playlist", {"title": playlist.title, "count": len(playlist.entries)})

        target = self.settings.output_dir
        if self.settings.playlist_folder and len(playlist.entries) > 1:
            target = target / safe_filename(playlist.title)
        if not self.settings.dry_run:
            target.mkdir(parents=True, exist_ok=True)

        report = RunReport(playlist=playlist.title, output_dir=target)
        total = len(playlist.entries)

        if self.settings.dry_run:
            for entry in playlist.entries:
                report.results.append(TrackResult(entry=entry, status="skipped"))
                self._emit("track_done", {"result": report.results[-1]})
            return report

        with ThreadPoolExecutor(max_workers=self.settings.concurrency) as pool:
            futures = {
                pool.submit(self._process, entry, target, total): entry
                for entry in playlist.entries
            }
            for future in as_completed(futures):
                entry = futures[future]
                try:
                    result = future.result()
                except Exception as exc:  # a worker crash must not sink the run
                    result = TrackResult(entry=entry, status="failed", error=str(exc))
                report.results.append(result)
                self._emit("track_done", {"result": result})

        report.results.sort(key=lambda r: r.entry.index)
        return report

    # Per-track pipeline

    def _process(self, entry: Entry, target: Path, total: int) -> TrackResult:
        settings = self.settings
        self._emit("track_start", {"entry": entry})

        if entry.video_id and entry.video_id in self._archive and not settings.overwrite:
            return TrackResult(entry=entry, status="skipped")

        try:
            info = self._probe(entry.url)
        except (DownloadError, ExtractorError) as exc:
            return TrackResult(entry=entry, status="failed", error=short_error(exc))

        name = parse_track(info)
        stem = build_stem(name, index=entry.index, number=settings.number)
        destination = target / f"{stem}.mp3"

        if destination.exists() and not settings.overwrite:
            self._archive.add(entry.video_id)
            return TrackResult(entry=entry, status="skipped", path=destination, name=name)

        try:
            path = self._download(entry.url, target, stem)
        except (DownloadError, ExtractorError) as exc:
            return TrackResult(entry=entry, status="failed", error=short_error(exc))

        cover = None
        if self._finder is not None:
            thumbnail = info.get("thumbnail") if settings.thumbnail_fallback else None
            cover = self._finder.find(name, thumbnail_url=thumbnail)
            if cover and settings.save_cover_file:
                path.with_suffix(".jpg").write_bytes(cover.data)

        try:
            tag_mp3(
                path,
                name,
                cover=cover,
                track_number=entry.index if settings.number else None,
                total_tracks=total if settings.number else None,
                album=settings.album,
                embed_cover=settings.embed_cover,
            )
        except Exception as exc:  # tags are a nicety; keep the audio either way
            self._emit("warning", {"entry": entry, "message": f"tagging failed: {exc}"})

        self._archive.add(entry.video_id)
        return TrackResult(
            entry=entry,
            status="downloaded",
            path=path,
            name=name,
            cover_source=cover.source if cover else None,
        )

    def _probe(self, url: str) -> dict[str, Any]:
        opts = _base_opts(self.settings) | {"skip_download": True, "noplaylist": True}
        with _ydl(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                raise ExtractorError(f"no metadata for {url}")
            # sanitize_info only returns None for a None input, which is ruled out above.
            return cast("dict[str, Any]", ydl.sanitize_info(info) or info)

    def _download(self, url: str, target: Path, stem: str) -> Path:
        opts = _base_opts(self.settings) | {
            "format": "bestaudio/best",
            "noplaylist": True,
            "outtmpl": {"default": str(target / f"{stem}.%(ext)s")},
            "overwrites": self.settings.overwrite,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": self.settings.quality,
                }
            ],
            "progress_hooks": [self._progress_hook(stem)],
        }
        with _ydl(opts) as ydl:
            info = ydl.extract_info(url, download=True)

        requested = (info or {}).get("requested_downloads") or []
        if requested and requested[0].get("filepath"):
            return Path(requested[0]["filepath"])
        return target / f"{stem}.mp3"

    def _progress_hook(self, stem: str) -> Callable[[dict[str, Any]], None]:
        def hook(status: dict[str, Any]) -> None:
            if status.get("status") != "downloading":
                return
            total = status.get("total_bytes") or status.get("total_bytes_estimate")
            self._emit(
                "progress",
                {
                    "stem": stem,
                    "downloaded": status.get("downloaded_bytes") or 0,
                    "total": total,
                },
            )

        return hook


def short_error(exc: Exception) -> str:
    """Strip the ANSI codes and `ERROR: ` prefix from a yt-dlp error."""
    text = str(exc).replace("\x1b[0;31m", "").replace("\x1b[0m", "")
    return text.removeprefix("ERROR: ").strip().splitlines()[0] if text else exc.__class__.__name__
