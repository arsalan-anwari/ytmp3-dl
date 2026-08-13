"""Video titles into an artist/title pair and a safe filename."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Bracketed junk: "(Official Video)", "[Lyric Video]", "(HD Remaster)", ...
_JUNK_IN_BRACKETS = re.compile(
    r"""[\(\[\{]\s*
        (?:[^()\[\]{}]*\b(?:
            official|video|videoclip|audio|lyrics?|lyric|visualizer|visualiser|hd|hq|4k|8k|
            full|free|download|mv|m/v|clip|performance|session|explicit|clean|
            music\s*video|with\s+lyrics|out\s+now|premiere|teaser|trailer
        )\b[^()\[\]{}]*)
    \s*[\)\]\}]""",
    re.IGNORECASE | re.VERBOSE,
)

# Trailing junk without brackets: "... | Official Video", "... - HD"
_JUNK_SUFFIX = re.compile(
    r"""\s*[|\-–—]\s*
        (?:official\s*(?:music\s*)?video|official\s*audio|lyrics?|lyric\s*video|
           music\s*video|audio|hd|hq|4k|visualizer|visualiser)
        \s*$""",
    re.IGNORECASE | re.VERBOSE,
)

# Separator between artist and title. En/em dashes and hyphens surrounded by spaces.
_ARTIST_SEP = re.compile(r"\s+[-–—]\s+|\s+[-–—]|[-–—]\s+")

_FEAT = re.compile(
    r"\s*[\(\[]?\s*\b(?:feat|ft|featuring|with)\.?\s+([^)\]]+?)\s*[\)\]]?\s*$",
    re.IGNORECASE,
)

# Uploader suffixes that are not part of the artist name.
_CHANNEL_SUFFIX = re.compile(r"\s*-\s*(?:topic|official|vevo|music|records?|tv)\s*$", re.IGNORECASE)

_ILLEGAL_FS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WS = re.compile(r"\s+")


@dataclass(slots=True)
class TrackName:
    artist: str | None
    title: str
    featuring: str | None = None

    @property
    def full_artist(self) -> str | None:
        """Artist plus featured performers, for tagging."""
        if self.artist and self.featuring:
            return f"{self.artist} feat. {self.featuring}"
        return self.artist

    @property
    def search_query(self) -> str:
        """Query for the metadata APIs; featured artists only hurt matching."""
        return f"{self.artist} {self.title}".strip() if self.artist else self.title


def strip_junk(text: str) -> str:
    """Remove the promotional noise uploaders append to titles."""
    cleaned = _JUNK_IN_BRACKETS.sub(" ", text)
    previous = None
    while previous != cleaned:
        previous = cleaned
        cleaned = _JUNK_SUFFIX.sub("", cleaned)
    cleaned = cleaned.strip(" -–—|·")
    return _WS.sub(" ", cleaned).strip()


def split_featuring(title: str) -> tuple[str, str | None]:
    match = _FEAT.search(title)
    if not match:
        return title.strip(), None
    return title[: match.start()].strip(" -–—([,"), match.group(1).strip()


def clean_uploader(uploader: str | None) -> str | None:
    """Read the artist out of an `Artist - Topic` or `ArtistVEVO` channel."""
    if not uploader:
        return None
    name = _CHANNEL_SUFFIX.sub("", uploader).strip()
    name = re.sub(r"VEVO$", "", name).strip()
    return name or None


def parse_track(info: dict) -> TrackName:
    """Prefer yt-dlp's music metadata, else parse the video title."""
    track = (info.get("track") or "").strip()
    artist = (info.get("artist") or info.get("creator") or "").strip()
    if track:
        # YouTube Music entries carry proper fields; artists come comma/`;`-separated.
        primary = re.split(r"\s*[,;]\s*|\s+&\s+", artist)[0] if artist else None
        title, featuring = split_featuring(strip_junk(track))
        return TrackName(
            artist=primary or clean_uploader(info.get("uploader")),
            title=title or track,
            featuring=featuring,
        )

    raw = strip_junk(info.get("title") or info.get("id") or "untitled")
    parts = _ARTIST_SEP.split(raw, maxsplit=1)
    if len(parts) == 2 and all(p.strip() for p in parts):
        candidate_artist, candidate_title = (p.strip() for p in parts)
    else:
        candidate_artist, candidate_title = None, raw

    if candidate_artist is None:
        candidate_artist = clean_uploader(info.get("uploader"))

    title, featuring = split_featuring(candidate_title)
    return TrackName(artist=candidate_artist or None, title=title or raw, featuring=featuring)


def safe_filename(text: str, max_length: int = 120) -> str:
    """Cross-platform stem: never empty, never a reserved name."""
    text = unicodedata.normalize("NFC", text)
    text = _ILLEGAL_FS.sub("_", text)
    text = _WS.sub(" ", text).strip(" .")
    if len(text) > max_length:
        text = text[:max_length].rstrip(" .")
    if not text:
        return "untitled"
    if text.upper() in {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }:
        text = f"_{text}"
    return text


def build_stem(name: TrackName, index: int | None = None, number: bool = False) -> str:
    base = f"{name.artist} - {name.title}" if name.artist else name.title
    if number and index is not None:
        base = f"{index:02d} - {base}"
    return safe_filename(base)
