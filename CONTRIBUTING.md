# Contributing to Spotify → YouTube Sync

First off — thank you for considering a contribution! Every improvement, no matter how small, helps the thousands of music lovers who use this tool. 🎵

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Commit Message Format](#commit-message-format)

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold these standards. Please report unacceptable behaviour to the maintainers via GitHub Issues.

---

## How Can I Contribute?

### 🐛 Reporting Bugs

Before filing a bug, please check the [existing Issues](https://github.com/Aakashm18/spotify-to-youtube-music-sync/issues) to avoid duplicates.

Use the **Bug Report** issue template and include:
- Your OS and Python version
- The exact error message / log output
- Steps to reproduce
- What you expected vs what happened

**Never post OAuth tokens, client IDs, or secrets in issues.**

### 💡 Suggesting Features

Open a **Feature Request** issue describing:
- The problem you're trying to solve
- Your proposed solution (or just the problem — that's fine too!)
- Any alternatives you've considered

### 🔧 Submitting Code Changes

1. Check the [open issues](https://github.com/Aakashm18/spotify-to-youtube-music-sync/issues) and [roadmap](README.md#-roadmap) for things to work on.
2. Comment on the issue to claim it before starting — avoid duplicate work.
3. Fork → branch → code → test → PR.

---

## Development Setup

### Prerequisites

- Python 3.10+
- `git`

### 1. Fork & Clone

```bash
git clone https://github.com/<your-username>/spotify-to-youtube-music-sync.git
cd spotify-to-youtube-music-sync
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 3. Install All Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Install Pre-commit Hooks

```bash
pre-commit install
```

This automatically runs linting and formatting checks on every commit.

### 5. Verify Your Setup

```bash
make lint   # or: flake8 . && black --check . && isort --check .
make test   # or: pytest
```

---

## Pull Request Process

1. **Branch naming**: Use a descriptive branch name:
   - `feat/playlist-sync` for new features
   - `fix/quota-handling` for bug fixes
   - `docs/improve-readme` for documentation
   - `chore/update-deps` for dependency updates

2. **Keep PRs focused**: One logical change per PR is far easier to review.

3. **Write tests**: New behaviour should include unit tests in `tests/`.

4. **Update docs**: If your change affects usage, update the README.

5. **Fill in the PR template**: Describe what, why, and how you tested it.

6. **CI must pass**: All checks (lint, type hints, tests) must be green.

7. A maintainer will review your PR within a reasonable timeframe.

---

## Coding Standards

| Tool | What it does | Config |
|------|-------------|--------|
| **black** | Code formatter (100-char lines) | `pyproject.toml` |
| **isort** | Import sorter (black-compatible) | `pyproject.toml` |
| **flake8** | Style linter | `.flake8` |
| **mypy** | Static type checker | `pyproject.toml` |

Run all checks at once:
```bash
make lint
```

Auto-format your code:
```bash
make fmt
```

---

## Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <short summary>

[optional body]

[optional footer]
```

**Types**: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`, `perf`

**Examples**:
```
feat(sync): add --since date filter for incremental syncs
fix(youtube): handle 429 rate-limit separately from 403 quota
docs(readme): add architecture diagram
chore(deps): bump google-api-python-client to 2.127.0
```

---

Thank you for helping make this the best open-source Spotify → YouTube sync engine! ⭐
