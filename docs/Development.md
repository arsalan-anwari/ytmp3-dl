# Development

```bash
git clone git@github.com:arsalan-anwari/ytmp3-dl.git
cd ytmp3-dl
uv sync
uv run pytest
uv run ruff check .
uv run ytmp3 "<url>" --dry-run
```

## Layout

| Module | Responsibility |
| --- | --- |
| `cli.py` | Flags, progress output, summary. |
| `config.py` | The `Settings` object shared by the pipeline. |
| `downloader.py` | Playlist extraction, worker pool, download archive. |
| `naming.py` | Title cleanup, artist/title splitting, safe filenames. |
| `covers.py` | Art providers, match scoring, image normalisation. |
| `tagging.py` | ID3 tags and embedded artwork. |

The distribution is `ytmp3-dl`, the import package and console command are both `ytmp3`.

`downloader.py` owns the flow: `fetch_playlist` flat-extracts the entries, then
`PlaylistDownloader` runs `_process` per entry on a thread pool, probe, download, convert,
look up art, tag. It reports through an `on_event` callback so `cli.py` can render progress
without the pipeline knowing about rich.

## Tests

`pytest`, no network. Parsing and image handling are pure functions and are tested directly;
the provider calls are not, so changes there need a manual run against a real playlist.

## Releasing

Version lives in one place, `src/ytmp3/__init__.py`; hatchling and the release script both read
it from there.

```bash
scripts/release.sh --bump 0.2.0    # edit __version__, update CHANGELOG
scripts/release.sh --dry-run       # checks + build, no upload
scripts/release.sh --test          # upload to TestPyPI
scripts/release.sh                 # upload to PyPI
scripts/release.sh --tag           # also create the v0.2.0 git tag
```

The script refuses to run on a dirty tree, runs ruff and pytest, rebuilds `dist/` from scratch,
and asks before uploading. Credentials come from `UV_PUBLISH_TOKEN` or a trusted-publisher
setup; nothing is stored in the repo.

## Syncing the wiki

`docs/` is the source; the GitHub wiki is a mirror. Filenames map directly to page names, so
`docs/Cover-Art.md` is the *Cover Art* page and `docs/Home.md` is the landing page. Keep the
directory flat. The wiki has no subdirectories and link between pages as `[Usage](Usage.md)`,
which works when browsing the repo; the sync script drops the `.md` so it works in the wiki too.

```bash
scripts/sync-wiki.sh --dry-run
scripts/sync-wiki.sh
```

It clones the wiki to `../ytmp3-dl.wiki`, copies `docs/` over it, and commits and pushes only
if something changed.
