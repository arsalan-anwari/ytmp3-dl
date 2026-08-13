"""Settings shared by the pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# yt-dlp maps "0" to the best VBR quality LAME can produce (~245 kbps average).
DEFAULT_QUALITY = "0"


@dataclass(slots=True)
class Settings:
    """Resolved CLI flags."""

    output_dir: Path
    quality: str = DEFAULT_QUALITY
    concurrency: int = 3
    limit: int | None = None
    playlist_items: str | None = None

    # Layout and tags
    playlist_folder: bool = True
    number: bool = False
    album: str | None = None

    # Cover art
    covers: bool = True
    cover_size: int = 600
    embed_cover: bool = True
    save_cover_file: bool = False
    thumbnail_fallback: bool = True

    # Bookkeeping
    archive: Path | None = None
    overwrite: bool = False
    dry_run: bool = False

    # Access
    cookies_file: Path | None = None
    cookies_from_browser: str | None = None

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir).expanduser()
        if self.archive is not None:
            self.archive = Path(self.archive).expanduser()
        if self.cookies_file is not None:
            self.cookies_file = Path(self.cookies_file).expanduser()
        self.concurrency = max(1, self.concurrency)
