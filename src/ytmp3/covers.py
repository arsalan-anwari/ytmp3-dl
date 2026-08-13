"""Album art lookup: iTunes, then Deezer, then the Cover Art Archive."""

from __future__ import annotations

import io
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from difflib import SequenceMatcher

import httpx
from PIL import Image

from . import __version__
from .naming import TrackName

USER_AGENT = f"ytmp3-dl/{__version__} (+https://github.com/arsalan-anwari/ytmp3-dl)"

# Below this title/artist similarity we assume the API matched the wrong song.
MATCH_THRESHOLD = 0.62


@dataclass(slots=True)
class Cover:
    data: bytes
    mime: str
    source: str
    album: str | None = None
    year: str | None = None
    genre: str | None = None
    album_artist: str | None = None


class _RateLimiter:
    """MusicBrainz asks for at most one request per second."""

    def __init__(self, min_interval: float) -> None:
        self._min_interval = min_interval
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            delay = self._min_interval - (time.monotonic() - self._last)
            if delay > 0:
                time.sleep(delay)
            self._last = time.monotonic()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.casefold().strip(), b.casefold().strip()).ratio()


def _score(name: TrackName, title: str, artist: str) -> float:
    """Weight the title over the artist; artist strings vary wildly."""
    title_score = _similarity(name.title, title)
    if not name.artist:
        return title_score
    return 0.7 * title_score + 0.3 * _similarity(name.artist, artist)


def _to_square_jpeg(data: bytes, size: int) -> tuple[bytes, str]:
    """Center-crop to a square and re-encode, so all art is uniform."""
    with Image.open(io.BytesIO(data)) as img:
        img = img.convert("RGB")
        side = min(img.size)
        left = (img.width - side) // 2
        top = (img.height - side) // 2
        img = img.crop((left, top, left + side, top + side))
        if img.width > size:
            img = img.resize((size, size), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=90, optimize=True)
    return buffer.getvalue(), "image/jpeg"


class CoverFinder:
    """Thread-safe lookup with a per-run in-memory cache."""

    def __init__(self, client: httpx.Client | None = None, size: int = 600) -> None:
        self._client = client or httpx.Client(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        self._size = size
        self._mb_limiter = _RateLimiter(1.05)
        self._cache: dict[tuple[str, str], Cover | None] = {}
        self._cache_lock = threading.Lock()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> CoverFinder:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def find(self, name: TrackName, thumbnail_url: str | None = None) -> Cover | None:
        key = ((name.artist or "").casefold(), name.title.casefold())
        with self._cache_lock:
            if key in self._cache:
                return self._cache[key]

        providers: list[Callable[[TrackName], Cover | None]] = [
            self._from_itunes,
            self._from_deezer,
            self._from_cover_art_archive,
        ]
        cover: Cover | None = None
        for provider in providers:
            try:
                cover = provider(name)
            except (httpx.HTTPError, ValueError, OSError):
                cover = None
            if cover is not None:
                break

        if cover is None and thumbnail_url:
            cover = self._from_thumbnail(thumbnail_url)

        with self._cache_lock:
            self._cache[key] = cover
        return cover

    def _fetch_image(self, url: str) -> bytes | None:
        response = self._client.get(url)
        if response.status_code != 200 or not response.content:
            return None
        return response.content

    # Providers

    def _from_itunes(self, name: TrackName) -> Cover | None:
        response = self._client.get(
            "https://itunes.apple.com/search",
            params={"term": name.search_query, "entity": "song", "limit": 8},
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        best, best_score = None, 0.0
        for item in results:
            score = _score(name, item.get("trackName", ""), item.get("artistName", ""))
            if score > best_score:
                best, best_score = item, score
        if best is None or best_score < MATCH_THRESHOLD:
            return None

        artwork = best.get("artworkUrl100") or best.get("artworkUrl60")
        if not artwork:
            return None
        # iTunes serves any resolution by rewriting the dimensions in the path.
        artwork = artwork.replace("100x100bb", f"{self._size}x{self._size}bb")
        artwork = artwork.replace("60x60bb", f"{self._size}x{self._size}bb")
        raw = self._fetch_image(artwork)
        if raw is None:
            return None

        data, mime = _to_square_jpeg(raw, self._size)
        release = best.get("releaseDate") or ""
        return Cover(
            data=data,
            mime=mime,
            source="itunes",
            album=best.get("collectionName"),
            year=release[:4] or None,
            genre=best.get("primaryGenreName"),
            album_artist=best.get("collectionArtistName") or best.get("artistName"),
        )

    def _from_deezer(self, name: TrackName) -> Cover | None:
        response = self._client.get(
            "https://api.deezer.com/search",
            params={"q": name.search_query, "limit": 8},
        )
        response.raise_for_status()
        results = response.json().get("data", []) or []
        best, best_score = None, 0.0
        for item in results:
            score = _score(
                name,
                item.get("title") or "",
                (item.get("artist") or {}).get("name", ""),
            )
            if score > best_score:
                best, best_score = item, score
        if best is None or best_score < MATCH_THRESHOLD:
            return None

        album = best.get("album") or {}
        artwork = album.get("cover_xl") or album.get("cover_big") or album.get("cover_medium")
        if not artwork:
            return None
        raw = self._fetch_image(artwork)
        if raw is None:
            return None

        data, mime = _to_square_jpeg(raw, self._size)
        return Cover(
            data=data,
            mime=mime,
            source="deezer",
            album=album.get("title"),
            album_artist=(best.get("artist") or {}).get("name"),
        )

    def _from_cover_art_archive(self, name: TrackName) -> Cover | None:
        query = f'recording:"{name.title}"'
        if name.artist:
            query += f' AND artist:"{name.artist}"'

        self._mb_limiter.wait()
        response = self._client.get(
            "https://musicbrainz.org/ws/2/recording",
            params={"query": query, "fmt": "json", "limit": 5},
        )
        response.raise_for_status()
        recordings = response.json().get("recordings", []) or []

        for recording in recordings:
            credits = recording.get("artist-credit") or [{}]
            artist_name = (credits[0].get("artist") or {}).get("name", "")
            if _score(name, recording.get("title", ""), artist_name) < MATCH_THRESHOLD:
                continue
            for release in recording.get("releases", [])[:3]:
                release_id = release.get("id")
                if not release_id:
                    continue
                size = 1200 if self._size > 500 else 500
                raw = self._fetch_image(
                    f"https://coverartarchive.org/release/{release_id}/front-{size}"
                )
                if raw is None:
                    continue
                data, mime = _to_square_jpeg(raw, self._size)
                date = release.get("date") or ""
                return Cover(
                    data=data,
                    mime=mime,
                    source="coverartarchive",
                    album=release.get("title"),
                    year=date[:4] or None,
                    album_artist=artist_name or None,
                )
        return None

    def _from_thumbnail(self, url: str) -> Cover | None:
        """Last resort: the video thumbnail, cropped to a square."""
        try:
            raw = self._fetch_image(url)
        except httpx.HTTPError:
            return None
        if raw is None:
            return None
        try:
            data, mime = _to_square_jpeg(raw, self._size)
        except OSError:
            return None
        return Cover(data=data, mime=mime, source="thumbnail")
