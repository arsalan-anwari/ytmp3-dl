# Troubleshooting

## "Requested format is not available"

The usual cause is a missing JavaScript runtime: YouTube offers nothing but storyboard images
until the "n challenge" is solved. Install `deno`, `node`, `bun` or `quickjs` and check it is on
your `PATH`. See [Installation](Installation.md).

If a runtime is present, yt-dlp itself may be behind. YouTube changes often, and yt-dlp releases
frequently:

```bash
uv tool upgrade ytmp3-dl        # or: pip install -U ytmp3-dl yt-dlp
```

## "Sign in to confirm you're not a bot"

YouTube wants a session. See [Cookies](Cookies.md).

## "ffmpeg not found" / files stay `.webm` or `.m4a`

ffmpeg does the MP3 conversion and is not bundled. Install it and check `ffmpeg -version`.

## Every track fails with the same error

Read the first failure rather than the last as they are usually one cause. Rerun with
`--concurrency 1` for readable output, and `--limit 1` to iterate quickly.

## Wrong or missing album art

Art is only accepted above a similarity threshold, so a badly parsed title yields no match.
Check what was parsed with `--dry-run`, and note that live versions, remixes and covers often
have no release to match against. Options: `--album` to force the album tag,
`--no-thumbnail-fallback` to leave non-matching tracks bare, or `--no-covers` to skip lookups
entirely.

## Wrong artist or title

The parser strips promotional noise (`(Official Video)`, `[HD]`, `| Lyrics`) and splits on a
spaced dash. Titles that use neither or that put the artist last will come out wrong, and
uploads without YouTube Music metadata are guessed from the channel name. Fix the tags
afterwards with a tag editor, or download those tracks individually with `--album`.

## Downloads are slow

Raise `--concurrency` (up to 16). Beyond about 6 the limit is usually YouTube throttling rather
than your connection, and heavy parallelism makes the bot check more likely.

## A rerun downloads everything again

Reruns skip existing files by name, so a different `--output`, `--number` or `--album` produces
different filenames and nothing matches. Use `--archive` to track video ids instead of
filenames.

## Reporting a bug

Include the ytmp3 version (`ytmp3 --version`), your OS, the output of `ffmpeg -version` and your
JS runtime version, the exact command, and the error. Never include your cookies file. Issues:
<https://github.com/arsalan-anwari/ytmp3-dl/issues>.
