"""Command line interface."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from . import __version__
from .config import DEFAULT_QUALITY, Settings
from .downloader import (
    EXTRACTION_ERRORS,
    PlaylistDownloader,
    RunReport,
    TrackResult,
    fetch_playlist,
    short_error,
)

app = typer.Typer(
    add_completion=False,
    help="Download a YouTube playlist as tagged MP3 files with cover art.",
)
console = Console()
error_console = Console(stderr=True)


def _show_version(value: bool) -> None:
    if value:
        console.print(f"ytmp3-dl {__version__}")
        raise typer.Exit()


@app.command()
def download(  # noqa: PLR0913; a CLI is allowed to have many flags
    url: str = typer.Argument(..., help="Playlist or video URL."),
    output: Path = typer.Option(
        Path("downloads"), "--output", "-o", help="Directory to write MP3s into."
    ),
    quality: str = typer.Option(
        DEFAULT_QUALITY,
        "--quality",
        "-q",
        help="LAME quality: 0-9 (0 = best VBR) or a bitrate like 320.",
    ),
    concurrency: int = typer.Option(
        3, "--concurrency", "-j", min=1, max=16, help="Tracks to download in parallel."
    ),
    limit: int | None = typer.Option(None, "--limit", help="Stop after N tracks."),
    items: str | None = typer.Option(
        None, "--items", help="yt-dlp playlist selection, e.g. '1-10,15,20-'."
    ),
    covers: bool = typer.Option(True, "--covers/--no-covers", help="Look up album art."),
    cover_size: int = typer.Option(600, "--cover-size", help="Cover edge length in pixels."),
    embed: bool = typer.Option(True, "--embed/--no-embed", help="Embed art in the MP3."),
    save_cover: bool = typer.Option(
        False, "--save-cover", help="Also write cover art next to the MP3 as .jpg."
    ),
    thumbnail_fallback: bool = typer.Option(
        True,
        "--thumbnail-fallback/--no-thumbnail-fallback",
        help="Use the video thumbnail when no album art is found.",
    ),
    number: bool = typer.Option(
        False, "--number", "-n", help="Prefix filenames with the playlist position."
    ),
    album: str | None = typer.Option(None, "--album", help="Force this album tag."),
    playlist_folder: bool = typer.Option(
        True, "--folder/--no-folder", help="Create a subfolder named after the playlist."
    ),
    archive: Path | None = typer.Option(
        None, "--archive", help="File of downloaded video ids; reruns skip them."
    ),
    overwrite: bool = typer.Option(False, "--overwrite", help="Re-download existing files."),
    dry_run: bool = typer.Option(False, "--dry-run", help="List the playlist and exit."),
    cookies: Path | None = typer.Option(
        None, "--cookies", help="Netscape cookies file, for private playlists."
    ),
    cookies_from_browser: str | None = typer.Option(
        None, "--cookies-from-browser", help="Load cookies from e.g. firefox, chrome."
    ),
    version: bool = typer.Option(  # noqa: ARG001 - consumed by the eager callback
        False,
        "--version",
        "-V",
        callback=_show_version,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    settings = Settings(
        output_dir=output,
        quality=quality,
        concurrency=concurrency,
        limit=limit,
        playlist_items=items,
        playlist_folder=playlist_folder,
        number=number,
        album=album,
        covers=covers,
        cover_size=cover_size,
        embed_cover=embed,
        save_cover_file=save_cover,
        thumbnail_fallback=thumbnail_fallback,
        archive=archive,
        overwrite=overwrite,
        dry_run=dry_run,
        cookies_file=cookies,
        cookies_from_browser=cookies_from_browser,
    )

    if dry_run:
        _dry_run(url, settings)
        return

    report = _run(url, settings)
    _summarise(report)
    if report.of("failed"):
        raise typer.Exit(code=1)


def _fail(exc: Exception) -> typer.Exit:
    error_console.print(f"[red]error[/red] {short_error(exc)}")
    return typer.Exit(code=1)


def _dry_run(url: str, settings: Settings) -> None:
    try:
        with console.status("Reading playlist..."):
            playlist = fetch_playlist(url, settings)
    except EXTRACTION_ERRORS as exc:
        raise _fail(exc) from exc

    table = Table(title=playlist.title, title_justify="left", header_style="bold")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Video")
    table.add_column("Id", style="dim")
    for entry in playlist.entries:
        table.add_row(str(entry.index), entry.title, entry.video_id)
    console.print(table)
    console.print(f"[dim]{len(playlist.entries)} track(s); nothing downloaded.[/dim]")


def _run(url: str, settings: Settings) -> RunReport:
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    )
    task_id: Any = None

    def on_event(name: str, data: dict[str, Any]) -> None:
        nonlocal task_id
        if name == "playlist":
            console.print(
                f"[bold]{data['title']}[/bold] — {data['count']} track(s)"
            )
            task_id = progress.add_task("Downloading", total=data["count"])
        elif name == "track_done" and task_id is not None:
            result: TrackResult = data["result"]
            progress.advance(task_id)
            progress.console.print(_line(result))
        elif name == "warning":
            progress.console.print(f"[yellow]warn[/yellow]  {data['message']}")

    with progress, PlaylistDownloader(settings, on_event=on_event) as downloader:
        try:
            return downloader.run(url)
        except EXTRACTION_ERRORS as exc:
            progress.stop()
            raise _fail(exc) from exc


def _line(result: TrackResult) -> str:
    label = result.name and (
        f"{result.name.full_artist} - {result.name.title}"
        if result.name.full_artist
        else result.name.title
    )
    label = label or result.entry.title
    if result.status == "downloaded":
        art = f" [dim](art: {result.cover_source})[/dim]" if result.cover_source else ""
        return f"[green]ok[/green]    {label}{art}"
    if result.status == "skipped":
        return f"[dim]skip  {label}[/dim]"
    return f"[red]fail[/red]  {label} [dim]{result.error or ''}[/dim]"


def _summarise(report: RunReport) -> None:
    done = report.of("downloaded")
    skipped = report.of("skipped")
    failed = report.of("failed")
    no_art = [r for r in done if r.cover_source is None]

    console.print()
    console.print(
        f"[bold]{len(done)} downloaded[/bold], {len(skipped)} skipped, "
        f"{len(failed)} failed → {report.output_dir}"
    )
    if no_art:
        console.print(f"[yellow]{len(no_art)} track(s) without cover art.[/yellow]")


def main() -> None:
    try:
        app()
    except KeyboardInterrupt:
        error_console.print("[yellow]interrupted[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    main()
