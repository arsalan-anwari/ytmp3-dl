import io

import pytest
from PIL import Image

from ytmp3.covers import _score, _to_square_jpeg
from ytmp3.naming import TrackName


def _png(width: int, height: int) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "red").save(buffer, format="PNG")
    return buffer.getvalue()


def test_score_rewards_exact_match():
    name = TrackName(artist="Some Artist", title="Some Song")
    assert _score(name, "Some Song", "Some Artist") == pytest.approx(1.0)
    assert _score(name, "Totally Different", "Nobody") < 0.5


def test_score_ignores_artist_when_unknown():
    name = TrackName(artist=None, title="Some Song")
    assert _score(name, "Some Song", "Anyone") == pytest.approx(1.0)


def test_to_square_jpeg_crops_widescreen_thumbnails():
    data, mime = _to_square_jpeg(_png(1280, 720), 600)
    assert mime == "image/jpeg"
    with Image.open(io.BytesIO(data)) as img:
        assert img.size == (600, 600)
        assert img.format == "JPEG"


def test_to_square_jpeg_does_not_upscale():
    data, _ = _to_square_jpeg(_png(300, 300), 600)
    with Image.open(io.BytesIO(data)) as img:
        assert img.size == (300, 300)
