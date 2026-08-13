# Cookies

YouTube increasingly answers with *"Sign in to confirm you're not a bot"*, and private or
age-gated playlists need an account either way. Both are solved by giving yt-dlp your session
cookies.

## From your browser

The safer option where nothing is written to disk.

```bash
ytmp3 "<url>" --cookies-from-browser firefox
```

Accepts `firefox`, `chrome`, `chromium`, `brave`, `edge`, `opera`, `safari`, `vivaldi`. Close
the browser first: Chromium-based browsers lock their cookie database while running.

## From a file

Export your cookies in Netscape format with a browser extension, then:

```bash
ytmp3 "<url>" --cookies cookies.txt
```

## Cookies expire

YouTube rotates session cookies, and an export goes stale after a while, often within days.
When downloads that used to work start failing the bot check again, export again.