# ytmp3-dl

Download a YouTube playlist as tagged MP3 files, with album art looked up automatically.

```bash
uv tool install ytmp3-dl
ytmp3 "https://www.youtube.com/playlist?list=PLxxxxxxxx"
```

Files land in `downloads/<Playlist Name>/Artist - Title.mp3`.

## What it does

Per track: extract the best audio stream with yt-dlp, convert to MP3 with ffmpeg, parse the
artist and title out of the video title, look up album art, write ID3v2.4 tags and embed the
cover. Tracks are processed in parallel, and a download archive lets a rerun resume.

## Pages

- **[Installation](Installation.md)** — install methods and the two external requirements.
- **[Usage](Usage.md)** — every flag, with examples.
- **[Cover Art](Cover-Art.md)** — which providers are tried, and how a match is accepted.
- **[Cookies](Cookies.md)** — private, age-gated and bot-checked playlists.
- **[Troubleshooting](Troubleshooting.md)** — common errors and what they mean.
- **[Development](Development.md)** — module layout, tests, releasing.

## Use

Downloading is subject to YouTube's Terms of Service and to the rights covering each video. Use
it for content you own, content licensed for reuse, or where you otherwise have permission.
