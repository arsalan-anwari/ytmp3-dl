"""ID3v2.4 tags and embedded cover art."""

from __future__ import annotations

from pathlib import Path

from mutagen.id3 import (
    APIC,
    ID3,
    TALB,
    TCON,
    TDRC,
    TIT2,
    TPE1,
    TPE2,
    TRCK,
    ID3NoHeaderError,
)

from .covers import Cover
from .naming import TrackName

# APIC picture type 3 = front cover.
FRONT_COVER = 3


def tag_mp3(
    path: Path,
    name: TrackName,
    cover: Cover | None = None,
    track_number: int | None = None,
    total_tracks: int | None = None,
    album: str | None = None,
    embed_cover: bool = True,
) -> None:
    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()

    tags.setall("TIT2", [TIT2(encoding=3, text=name.title)])

    if name.full_artist:
        tags.setall("TPE1", [TPE1(encoding=3, text=name.full_artist)])

    album_name = album or (cover.album if cover else None)
    if album_name:
        tags.setall("TALB", [TALB(encoding=3, text=album_name)])

    album_artist = (cover.album_artist if cover else None) or name.artist
    if album_artist:
        tags.setall("TPE2", [TPE2(encoding=3, text=album_artist)])

    if cover and cover.year:
        tags.setall("TDRC", [TDRC(encoding=3, text=cover.year)])
    if cover and cover.genre:
        tags.setall("TCON", [TCON(encoding=3, text=cover.genre)])

    if track_number:
        value = f"{track_number}/{total_tracks}" if total_tracks else str(track_number)
        tags.setall("TRCK", [TRCK(encoding=3, text=value)])

    if cover and embed_cover:
        tags.delall("APIC")
        tags.add(
            APIC(
                encoding=3,
                mime=cover.mime,
                type=FRONT_COVER,
                desc="Cover",
                data=cover.data,
            )
        )

    tags.save(path, v2_version=4)
