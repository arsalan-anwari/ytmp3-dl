# ytmp3-dl

Download a YouTube playlist as tagged MP3 files, with album art looked up automatically.

- Extracts the best audio stream with [yt-dlp](https://github.com/yt-dlp/yt-dlp), converts it with ffmpeg.
- Parses `Artist - Title` out of messy video titles, preferring YouTube Music metadata.
- Finds real album art on iTunes, Deezer and the Cover Art Archive; falls back to the thumbnail.
- Writes ID3v2.4 tags (title, artist, album, year, genre, track number) and embeds the cover.
- Keeps a download archive, so reruns resume instead of starting over.

## Requirements

- Python 3.10+
- `ffmpeg` on your `PATH`
- A JavaScript runtime on your `PATH`: `deno`, `node`, `bun` or `quickjs` — YouTube hides its
  audio formats behind a JS "n challenge", and without a runtime every download fails.

## Install

```bash
uv tool install ytmp3-dl     # isolated, on your PATH
pipx install ytmp3-dl        # same, via pipx
pip install ytmp3-dl         # into the current environment
uvx ytmp3-dl "<url>"         # no install, one-off run
```

## Usage

```bash
ytmp3 "https://www.youtube.com/playlist?list=PLxxxxxxxx"
```

Files land in `downloads/<Playlist Name>/Artist - Title.mp3`. Use `--dry-run` to see the track
list first, and `ytmp3 --help` for every flag.

```bash
ytmp3 "<url>" --output ~/Music --quality 320 --concurrency 4 --number --save-cover
```

Private or age-gated playlists need cookies:

```bash
ytmp3 "<url>" --cookies-from-browser firefox
```

## Documentation

Full docs live in the [wiki](https://github.com/arsalan-anwari/ytmp3-dl/wiki), and in
[docs/](docs/) in this repo:

| Page | Contents |
| --- | --- |
| [Installation](docs/Installation.md) | Install methods, ffmpeg, JS runtimes. |
| [Usage](docs/Usage.md) | Every flag, with examples. |
| [Cover Art](docs/Cover-Art.md) | How art is found, scored and embedded. |
| [Cookies](docs/Cookies.md) | Getting past "Sign in to confirm you're not a bot". |
| [Troubleshooting](docs/Troubleshooting.md) | Common errors and fixes. |
| [Development](docs/Development.md) | Layout, tests, release process. |

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
```

## Licence and use

Apache-2.0, see [LICENSE](LICENSE). Downloading is subject to YouTube's Terms of Service and to
the rights covering each video. Use it for content you own, content licensed for reuse, or where
you otherwise have permission.
