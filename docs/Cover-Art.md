# Cover art

Every track gets an image, unless you pass `--no-covers`.

## Providers

The parsed artist and title are queried against three free APIs, in order, stopping at the first
accepted match:

1. **iTunes Search**: best hit rate, and serves any resolution you ask for.
2. **Deezer**: good coverage of releases iTunes misses.
3. **MusicBrainz Cover Art Archive**: rate-limited to one request per second.

If none match and `--thumbnail-fallback` is on (the default), the video thumbnail is used
instead. `--no-thumbnail-fallback` leaves those tracks bare.

## Accepting a match

A result is only accepted if it looks like the same song. Title and artist similarity are scored
with a sequence ratio and weighted 70/30 toward the title and artist strings vary far more between
providers. The result is rejected below **0.62**.

That threshold is what keeps a track called "Home" from picking up the artwork of an unrelated
song with the same name. The cost is the occasional track with no album art; the summary line at
the end reports how many.

## The image

The winning image is centre-cropped to a square, resized down to `--cover-size` (600px default)
and re-encoded as JPEG at quality 90. Every file in a playlist therefore ends up with art of the
same shape and size, including thumbnails, which are cropped from 16:9.

By default the art is embedded in the MP3 as an ID3 `APIC` front-cover frame. `--no-embed`
leaves the audio untouched; `--save-cover` also writes the JPEG next to the MP3.

## Tags that come with the art

A provider match carries more than an image, and what it carries fills in the tags:

| Tag | Source |
| --- | --- |
| Album (`TALB`) | `--album` if given, else the matched release. |
| Album artist (`TPE2`) | The matched release artist, else the parsed artist. |
| Year (`TDRC`) | iTunes or Cover Art Archive release date. |
| Genre (`TCON`) | iTunes primary genre. |

Title, artist and track number come from the video metadata rather than the art lookup, so they
are set even with `--no-covers`.

## Caching

Lookups are cached per run, keyed on artist and title, so a playlist that repeats a track only
queries once. The cache is in memory and does not persist between runs.
