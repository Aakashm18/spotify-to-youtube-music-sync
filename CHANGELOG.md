# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] — 2026-02-21

### Added
- **CLI flags** for `youtube.py`: `--dry-run`, `--since YYYY-MM-DD`, `--verbose`
  - `--dry-run`: Preview what would be synced without touching the YouTube API
  - `--since`: Sync only songs liked on or after a given date (great for catching up)
  - `--verbose`: Enable DEBUG-level log output
- **Smart YouTube search** with multiple fallback strategies:
  - Tries "official music video" → "official audio" → "lyric video" → bare query
  - Maximises the chance of finding the right video, especially for popular tracks
- **GitHub Actions Step Summary**: Each run now writes a Markdown summary table
  visible directly in the Actions run page (new songs added, skipped, errors)
- **Manual dispatch inputs** in `sync.yml`: `dry_run` and `since` can be set from the
  GitHub Actions UI without editing the workflow file
- **Concurrency protection** in `sync.yml`: prevents two overlapping runs from
  hammering the YouTube API simultaneously
- `pyproject.toml` with full project metadata and tool configs (black, isort, mypy, pytest)
- `requirements-dev.txt` for linting, testing, and pre-commit dependencies
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`
- `CHANGELOG.md` (this file)
- `.github/ISSUE_TEMPLATE/` with bug report and feature request templates
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/dependabot.yml` for automated dependency updates
- `.github/workflows/ci.yml` — CI pipeline (lint + tests) runs on every PR
- `.pre-commit-config.yaml` — pre-commit hooks for local development
- `Makefile` with `make lint`, `make fmt`, `make test`, `make sync`, `make dedup`
- `Dockerfile` for containerised local runs (no Python setup required)
- `tests/` directory with unit tests for core sync and deduplication logic
- Error count tracking and reporting in sync summary

### Changed
- `sync()` now returns `(new_count, skip_count, error_count)` instead of `(new_count, skip_count)`
- Tracks with no YouTube match are now marked as processed (prevents infinite retries)
- `save_processed()` no longer crashes the run on `OSError` — logs and continues
- README overhauled: architecture diagram, value proposition, badges, roadmap, FAQ

### Fixed
- Potential state file corruption when disk write fails mid-run (now uses atomic rename)

---

## [1.0.0] — 2026-02-10

### Added
- Initial public release
- `youtube.py`: Full Spotify Liked Songs → YouTube playlist sync engine
  - Pagination support for unlimited library sizes
  - Idempotent processing via `processed_tracks.json`
  - Exponential-backoff retry on HTTP 5xx errors
  - Graceful YouTube quota exhaustion detection
  - Rotating file + stdout logging
- `remove_duplicates.py`: Detect and remove duplicate videos from a YouTube playlist
  - `--dry-run` mode supported
- `scripts/get_tokens.py`: Interactive one-time OAuth token helper for Spotify and YouTube
- `.github/workflows/sync.yml`: Daily cron GitHub Actions workflow
- `requirements.txt` with pinned production dependencies
- MIT License
- Comprehensive README with step-by-step setup guide

---

[1.1.0]: https://github.com/Aakashm18/spotify-to-youtube-music-sync/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Aakashm18/spotify-to-youtube-music-sync/releases/tag/v1.0.0
