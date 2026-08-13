# Usage

```bash
ytmp3 "<url>" [options]
```

The URL can be a playlist or a single video; a single video is treated as a one-track playlist.

## Flags

| Flag | Default | What it does |
| --- | --- | --- |
| `-o, --output` | `downloads` | Destination directory. |
| `-q, --quality` | `0` | LAME quality `0`–`9` (0 = best VBR) or a bitrate such as `320`. |
| `-j, --concurrency` | `3` | Tracks downloaded in parallel (1–16). |
| `--limit` | – | Stop after N tracks. |
| `--items` | – | yt-dlp playlist selection, e.g. `1-10,15,20-`. |
| `--covers / --no-covers` | on | Look up album art. |
| `--cover-size` | `600` | Cover edge length in pixels. |
| `--embed / --no-embed` | on | Embed the art in the MP3. |
| `--save-cover` | off | Also write the art next to the MP3 as `.jpg`. |
| `--thumbnail-fallback / --no-thumbnail-fallback` | on | Use the video thumbnail when no album art matches. |
| `-n, --number` | off | Prefix filenames with the playlist position, and set the track number tag. |
| `--album` | – | Force a specific album tag. |
| `--folder / --no-folder` | on | Create a subfolder named after the playlist. |
| `--archive` | – | File of downloaded video ids; listed ids are skipped on rerun. |
| `--overwrite` | off | Re-download files that already exist. |
| `--dry-run` | off | Print the track list and exit. |
| `--cookies` | – | Netscape cookies file. See [Cookies](Cookies.md). |
| `--cookies-from-browser` | – | Load cookies straight from `firefox`, `chrome`, … |
| `-V, --version` | – | Print the version and exit. |

## Examples

See what would be downloaded, without downloading:

```bash
ytmp3 "<url>" --dry-run
```

An album, numbered, into your music library:

```bash
ytmp3 "<url>" --output ~/Music --number --album "Album Name"
```

Higher quality, more parallelism, cover art also written beside each file:

```bash
ytmp3 "<url>" --quality 320 --concurrency 6 --save-cover
```

Only part of a long playlist:

```bash
ytmp3 "<url>" --items 1-20        # first twenty
ytmp3 "<url>" --limit 5           # first five
```

A playlist you top up over time where the archive makes reruns skip what you already have:

```bash
ytmp3 "<url>" --output ~/Music --archive ~/Music/.ytmp3-archive.txt
```

## Output layout

```
downloads/
└── Playlist Name/
    ├── Artist - Title.mp3
    └── Artist - Title.jpg     # only with --save-cover
```

`--no-folder` writes straight into the output directory, and a single-video URL never creates a
subfolder. Filenames are sanitised for every platform: illegal characters become `_`, names are
capped at 120 characters, and Windows reserved names like `CON` get a `_` prefix.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Everything downloaded or skipped. |
| `1` | At least one track failed, or the playlist could not be read. |
| `130` | Interrupted with Ctrl-C. |

## Reruns and skipping

A track is skipped when its target file already exists, or when its video id is in the
`--archive` file. `--overwrite` ignores both and downloads again.
