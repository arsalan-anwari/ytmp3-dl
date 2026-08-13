# Installation

## The package

The distribution is `ytmp3-dl`; the command it installs is `ytmp3`.

```bash
uv tool install ytmp3-dl     # isolated, on your PATH (recommended)
pipx install ytmp3-dl        # same, via pipx
pip install ytmp3-dl         # into the current environment
uvx ytmp3-dl "<url>"         # no install, one-off run
```

Upgrade with `uv tool upgrade ytmp3-dl`, `pipx upgrade ytmp3-dl` or `pip install -U ytmp3-dl`.

From a checkout:

```bash
uv sync                      # dev environment, run via `uv run ytmp3`
uv tool install --editable . # editable install on your PATH
```

## ffmpeg

yt-dlp hands the audio to ffmpeg for the MP3 conversion, so it has to be on your `PATH`.

```bash
dnf install ffmpeg       # Fedora
apt install ffmpeg       # Debian/Ubuntu
brew install ffmpeg      # macOS
winget install ffmpeg    # Windows
```

Check with `ffmpeg -version`.

## A JavaScript runtime

YouTube hides its audio formats behind a JavaScript "n challenge". Without a runtime to solve it
yt-dlp is offered storyboard images only, and every download fails with *"Requested format is
not available"*.

Any one of `deno`, `node`, `bun` or `quickjs` works. yt-dlp on its own only looks for `deno`;
ytmp3 enables whichever of the four it finds.

```bash
dnf install deno         # or nodejs, bun, quickjs
brew install deno
```

Check with `deno --version` (or `node --version`).

## Python

Python 3.10 or newer. `uv tool install` and `pipx` bring their own interpreter environment, so
nothing else is needed.
