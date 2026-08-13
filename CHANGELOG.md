# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] - 2026-08-13

No behaviour changes; the code is identical apart from formatting.

### Added

- GitHub Actions CI: ruff, pytest on 3.10-3.13, and a build checked with twine.
- `scripts/test_ci.sh` to run the same gate locally.
- Status badges on the README, which is also the PyPI project page.

### Fixed

- An invalid `# noqa` directive in `cli.py` that ruff discarded instead of applying.

## [1.0.0] - 2026-08-13

Initial release.

- Download a playlist or single video as MP3 via yt-dlp and ffmpeg.
- Parse `Artist - Title` from video titles, preferring YouTube Music metadata.
- Look up album art on iTunes, Deezer and the Cover Art Archive.
- Write ID3v2.4 tags and embed the cover.
- Download archive so reruns resume.

[Unreleased]: https://github.com/arsalan-anwari/ytmp3-dl/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/arsalan-anwari/ytmp3-dl/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/arsalan-anwari/ytmp3-dl/releases/tag/v1.0.0
