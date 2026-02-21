<div align="center">

# 🎵 Spotify → YouTube Music Sync

**Automatically mirror your Spotify Liked Songs to a YouTube playlist — forever, for free, using GitHub Actions.**

[![GitHub Actions](https://img.shields.io/badge/Powered%20by-GitHub%20Actions-2088FF?logo=github-actions&logoColor=white)](https://github.com/features/actions)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![CI](https://github.com/Aakashm18/spotify-to-youtube-music-sync/actions/workflows/ci.yml/badge.svg)](https://github.com/Aakashm18/spotify-to-youtube-music-sync/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](CHANGELOG.md)

</div>

---

## 📖 Table of Contents

1. [What This Does](#-what-this-does)
2. [How It Works](#️-how-it-works)
3. [Project Structure](#-project-structure)
4. [Prerequisites](#-prerequisites)
5. [Step 1 — Spotify Setup](#-step-1--spotify-app-setup)
6. [Step 2 — Google / YouTube Setup](#-step-2--google--youtube-api-setup)
7. [Step 3 — Get Your OAuth Tokens](#-step-3--get-your-oauth-refresh-tokens)
8. [Step 4 — Fork & Configure GitHub Actions](#-step-4--fork--configure-github-actions)
9. [Step 5 — Add GitHub Secrets](#-step-5--add-github-secrets)
10. [Step 6 — Run & Verify](#️-step-6--run--verify)
11. [CLI Flags](#-cli-flags)
12. [Docker Support](#-docker-support)
13. [Makefile Commands](#️-makefile-commands)
14. [Remove Duplicates](#-bonus-remove-duplicate-videos)
15. [Customisation](#️-customisation)
16. [Troubleshooting](#-troubleshooting)
17. [FAQ](#-faq)
18. [Contributing](#-contributing)
19. [License](#-license)

---

## 🎯 What This Does

| Feature | Detail |
|---------|--------|
| **Daily auto-sync** | Runs every day at 02:00 UTC via GitHub Actions (completely free) |
| **Incremental** | Only adds songs you haven't synced before — never re-adds duplicates |
| **Smart search** | Multi-strategy YouTube search (music video → official audio → lyric video → bare query) |
| **Quota-safe** | Detects YouTube API quota exhaustion and stops gracefully, resuming tomorrow |
| **Persistent state** | Tracks processed songs in `processed_tracks.json`, committed back to your repo |
| **CLI flags** | `--dry-run`, `--since YYYY-MM-DD`, `--verbose` for flexible local use |
| **Duplicate cleaner** | Separate script to remove any duplicate videos already in your YouTube playlist |
| **Run summaries** | Each Actions run writes a Markdown summary table visible in the Actions tab |
| **Docker support** | Run locally in a container — no Python setup required |
| **Zero cost** | Runs entirely within GitHub's free tier (2 000 minutes/month) |
| **Manual trigger** | One-click "Run workflow" button with optional `dry_run` and `since` inputs |
| **Concurrency protection** | Prevents two overlapping runs from hammering the YouTube API simultaneously |

---

## ⚙️ How It Works

```
┌─────────────┐       ┌───────────────────────────┐       ┌──────────────────────┐
│   Spotify   │──────▶│  youtube.py (Python)      │──────▶│  YouTube Playlist    │
│ Liked Songs │  API  │  • Fetch all songs        │  API  │  • Adds new songs    │
│             │       │  • Skip processed         │       │  • Skips duplicates  │
└─────────────┘       │  • Smart YouTube search   │       └──────────────────────┘
                      │  • Add to playlist        │
                      │  • Save state →           │       ┌──────────────────────┐
                      └───────────────────────────┘──────▶│ processed_tracks.json│
                                                           │ (committed to repo)  │
                                                           └──────────────────────┘
```

**The flow on every GitHub Actions run:**

1. Authenticate with Spotify using your stored refresh token
2. Fetch all your liked songs (handles pagination for unlimited library sizes)
3. Load `processed_tracks.json` to know which songs were already added
4. For each **new** song: try multiple YouTube search strategies to find the best match, then add it to your playlist
5. Save the updated `processed_tracks.json` back to the repo
6. Write a Markdown run summary (new songs added, skipped, errors) to the Actions tab

---

## 📁 Project Structure

```
spotify-to-youtube-music-sync/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── dependabot.yml                # Automated dependency updates
│   └── workflows/
│       ├── sync.yml                  # Daily sync (with dry_run + since inputs)
│       └── ci.yml                    # CI: lint + tests on every PR
├── scripts/
│   └── get_tokens.py                 # One-time helper to get OAuth refresh tokens
├── tests/
│   ├── __init__.py
│   ├── test_sync.py                  # Unit tests for sync logic
│   └── test_dedup.py                 # Unit tests for deduplication logic
├── youtube.py                        # Main sync script (with CLI flags)
├── remove_duplicates.py              # Optional: cleans duplicate playlist entries
├── processed_tracks.json             # Auto-managed state file (committed by Actions)
├── requirements.txt                  # Production dependencies
├── requirements-dev.txt              # Dev/lint/test dependencies
├── pyproject.toml                    # Project metadata + tool config (black, isort, mypy, pytest)
├── Makefile                          # Developer shortcuts (lint, fmt, test, sync, dedup…)
├── Dockerfile                        # Containerised local runs
├── .pre-commit-config.yaml           # Pre-commit hooks for local development
├── .flake8                           # Flake8 configuration
├── CHANGELOG.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── LICENSE
└── README.md
```

---

## 📋 Prerequisites

Before you start, you'll need:

- A **GitHub account** (free) — to fork this repo and use Actions
- A **Spotify account** (free or Premium)
- A **Google account** (the same one with your YouTube)
- **Python 3.10+** installed locally — only needed once for the token setup (or use Docker)

---

## 🟢 Step 1 — Spotify App Setup

You need a Spotify Developer App to get an API key.

### 1.1 Create a Spotify App

1. Go to **[Spotify Developer Dashboard](https://developer.spotify.com/dashboard)** and log in.
2. Click **"Create app"**.

   | Field | Value |
   |-------|-------|
   | App name | `spotify-to-youtube-music-sync` (or anything you like) |
   | App description | `Sync liked songs to YouTube` |
   | Redirect URI | `http://localhost:8888/callback` |
   | APIs to use | ✅ Web API |

3. Accept the terms and click **Save**.

### 1.2 Copy Your Credentials

4. On your app's dashboard, click **Settings**.
5. Note down:
   - **Client ID** → will become `SPOTIFY_CLIENT_ID`
   - **Client secret** → will become `SPOTIFY_CLIENT_SECRET`

> [!IMPORTANT]
> The Redirect URI **must** be exactly `http://localhost:8888/callback` — any difference will cause authentication to fail.

---

## 🔴 Step 2 — Google / YouTube API Setup

You need a Google Cloud project with the YouTube Data API v3 enabled.

### 2.1 Create a Google Cloud Project

1. Go to **[Google Cloud Console](https://console.cloud.google.com/)** and sign in.
2. Click the project dropdown at the top → **"New Project"**.
3. Give it a name (e.g. `spotify-to-youtube-music-sync`) and click **Create**.

### 2.2 Enable the YouTube Data API v3

4. In the left menu: **APIs & Services → Library**.
5. Search for `YouTube Data API v3`.
6. Click it, then click **Enable**.

### 2.3 Configure the OAuth Consent Screen

7. In the left menu: **APIs & Services → OAuth consent screen**.
8. Select **External** and click **Create**.

   Fill in the required fields:
   | Field | Value |
   |-------|-------|
   | App name | `Spotify YouTube Sync` |
   | User support email | Your Gmail address |
   | Developer contact email | Your Gmail address |

9. Click **Save and Continue** through the Scopes step (no changes needed).
10. On the **Test users** step — click **+ Add Users** and add your own Google email address.
    > ⚠️ This is **critical**. Without adding yourself as a test user, authentication will fail.
11. Click **Save and Continue**, then **Back to Dashboard**.

### 2.4 Create OAuth 2.0 Credentials

12. In the left menu: **APIs & Services → Credentials**.
13. Click **+ Create Credentials → OAuth Client ID**.

    | Field | Value |
    |-------|-------|
    | Application type | **Desktop app** |
    | Name | `Spotify YouTube Sync` |

14. Click **Create**.
15. Note down:
    - **Client ID** → will become `YOUTUBE_CLIENT_ID`
    - **Client secret** → will become `YOUTUBE_CLIENT_SECRET`

### 2.5 Get Your YouTube Playlist ID

16. Open **[YouTube Music](https://music.youtube.com/)** or **[YouTube](https://www.youtube.com/)** in your browser.
17. Create a new playlist (or use an existing one) that will receive your Spotify songs.
18. Open the playlist. Look at the URL:
    ```
    https://www.youtube.com/playlist?list=PLxxxxxxxxxxxxxxxxxxxx
    ```
    The part after `list=` is your **Playlist ID** → will become `PLAYLIST_ID`.

---

## 🔑 Step 3 — Get Your OAuth Refresh Tokens

Refresh tokens let the GitHub Actions workflow authenticate on your behalf — without you having to click "Authorise" every day.

> [!NOTE]
> You do this **once on your local machine**. The tokens are printed to your terminal only and should be immediately saved as GitHub Secrets. They are never written to disk by the script.

### 3.1 Install Python dependencies locally

Open a terminal in the project folder and run:

```bash
pip install spotipy google-auth-oauthlib
```

### 3.2 Run the token helper script

```bash
python scripts/get_tokens.py
```

The script will:

1. **Spotify step**: Ask for your Spotify Client ID & Secret, open a browser window, and ask you to paste back the redirect URL you land on after authorising.
2. **YouTube step**: Ask for your Google Client ID & Secret, open a browser window for Google sign-in, and automatically capture the token.

At the end, it will print five values to your terminal:

```
✅ Spotify Refresh Token (save this as SPOTIFY_REFRESH_TOKEN):
   BQBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

✅ YouTube Refresh Token (save this as YOUTUBE_REFRESH_TOKEN):
   1//0gxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

   Also save:
     YOUTUBE_CLIENT_ID     = 1234567890-xxxxxxxxxxxxxxxx.apps.googleusercontent.com
     YOUTUBE_CLIENT_SECRET = GOCSPX-xxxxxxxxxxxxxxxxxxxxxxx
```

**Copy these values carefully.** You'll need all seven pieces:

| Secret Name | Where to get it |
|-------------|-----------------|
| `SPOTIFY_CLIENT_ID` | Spotify Dashboard → App Settings |
| `SPOTIFY_CLIENT_SECRET` | Spotify Dashboard → App Settings |
| `SPOTIFY_REFRESH_TOKEN` | Printed by `get_tokens.py` |
| `YOUTUBE_CLIENT_ID` | Google Cloud → Credentials |
| `YOUTUBE_CLIENT_SECRET` | Google Cloud → Credentials |
| `YOUTUBE_REFRESH_TOKEN` | Printed by `get_tokens.py` |
| `PLAYLIST_ID` | From your YouTube playlist URL |

---

## 🍴 Step 4 — Fork & Configure GitHub Actions

### 4.1 Fork this repository

1. Click the **Fork** button at the top-right of this page.
2. Choose your account. GitHub will create `your-username/spotify-to-youtube-music-sync`.

### 4.2 Verify the workflow file

The file `.github/workflows/sync.yml` is already included. You don't need to edit it.  
It will automatically run every day at 02:00 UTC and can also be triggered manually with optional `dry_run` and `since` inputs.

---

## 🔐 Step 5 — Add GitHub Secrets

GitHub Secrets are encrypted environment variables — your tokens never appear in logs.

1. Go to your **forked repository** on GitHub.
2. Click **Settings** (the gear icon in the top navigation bar of your repo).
3. In the left sidebar: **Secrets and variables → Actions**.
4. Click **"New repository secret"** for each of the seven secrets:

   | Secret Name | Value |
   |-------------|-------|
   | `SPOTIFY_CLIENT_ID` | From Spotify Dashboard |
   | `SPOTIFY_CLIENT_SECRET` | From Spotify Dashboard |
   | `SPOTIFY_REFRESH_TOKEN` | From `get_tokens.py` output |
   | `YOUTUBE_CLIENT_ID` | From Google Cloud Console |
   | `YOUTUBE_CLIENT_SECRET` | From Google Cloud Console |
   | `YOUTUBE_REFRESH_TOKEN` | From `get_tokens.py` output |
   | `PLAYLIST_ID` | From your YouTube playlist URL |

> [!TIP]
> Double-check for extra spaces when pasting token values — they're a common source of auth errors.

After adding all seven secrets, your Secrets page should look like this:

```
Actions secrets and variables
 Repository secrets (7)
  ✓ PLAYLIST_ID
  ✓ SPOTIFY_CLIENT_ID
  ✓ SPOTIFY_CLIENT_SECRET
  ✓ SPOTIFY_REFRESH_TOKEN
  ✓ YOUTUBE_CLIENT_ID
  ✓ YOUTUBE_CLIENT_SECRET
  ✓ YOUTUBE_REFRESH_TOKEN
```

---

## ▶️ Step 6 — Run & Verify

### 6.1 Trigger a manual run

1. Go to your repository → **Actions** tab.
2. Click **"🎵 Spotify → YouTube Sync"** in the left sidebar.
3. Click **"Run workflow"** → optionally fill in `dry_run` or `since` → **"Run workflow"**.

### 6.2 Watch the logs

The run will show you each step. In the "▶️ Run Spotify → YouTube Sync" step you should see output like:

```
2024-01-15 02:00:12 | INFO     | ============================================================
2024-01-15 02:00:12 | INFO     |   Spotify → YouTube Sync  —  starting run
2024-01-15 02:00:12 | INFO     | ============================================================
2024-01-15 02:00:13 | INFO     | ✅ Spotify authenticated.
2024-01-15 02:00:14 | INFO     | ✅ YouTube authenticated.
2024-01-15 02:00:15 | INFO     | 🎵 Total Spotify liked songs: 312
2024-01-15 02:00:15 | INFO     | 📋 Already processed: 0 tracks
2024-01-15 02:00:17 | INFO     | ✅ Added: Blinding Lights — The Weeknd
2024-01-15 02:00:18 | INFO     | ✅ Added: Shape of You — Ed Sheeran
...
2024-01-15 02:05:44 | INFO     | ✅ New songs added : 95
2024-01-15 02:05:44 | INFO     | ⏭️  Skipped (done)  : 0
2024-01-15 02:05:44 | INFO     | ❌ Errors           : 0
```

A **Markdown summary table** (new / skipped / errors) is also written directly to the Actions run page under the "Summary" tab.

### 6.3 Check your YouTube playlist

Open your YouTube playlist — the songs should be there! After the first run, the `processed_tracks.json` file in your repository will be updated and committed automatically.

> [!NOTE]
> **YouTube API daily quota**: The YouTube Data API v3 has a default quota of **10,000 units/day**. Each search costs ~100 units and each playlist insert costs ~50 units. This means roughly **66 new songs per day** can be synced. If you have a large library, the sync will automatically continue across multiple days — picking up where it left off each time.

---

## 🖥️ CLI Flags

`youtube.py` supports the following flags for local or advanced use:

```bash
python youtube.py [OPTIONS]
```

| Flag | Description |
|------|-------------|
| `--dry-run` | Preview what would be synced without touching the YouTube API |
| `--since YYYY-MM-DD` | Only sync songs liked on or after this date |
| `--verbose` | Enable DEBUG-level log output |

**Examples:**

```bash
# Preview what would be added (safe — no changes)
python youtube.py --dry-run --verbose

# Catch up on songs liked since a specific date
python youtube.py --since 2025-06-01

# Full verbose sync
python youtube.py --verbose
```

These flags can also be set from the **GitHub Actions UI** when triggering a manual run — no workflow file edits needed.

---

## 🐳 Docker Support

Run the sync in a container without any local Python setup:

```bash
# Build the image
docker build -t spotify-to-youtube-music-sync .

# Run with an env file
docker run --env-file .env spotify-to-youtube-music-sync

# Persist processed_tracks.json across runs (mount a volume)
docker run --env-file .env -v $(pwd)/data:/data spotify-to-youtube-music-sync

# Dry-run inside Docker
docker run --env-file .env spotify-to-youtube-music-sync --dry-run --verbose
```

Create a `.env` file (not committed to git) with all seven variables:

```env
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REFRESH_TOKEN=...
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...
YOUTUBE_REFRESH_TOKEN=...
PLAYLIST_ID=...
```

> [!TIP]
> Mount `-v /host/path:/data` to store `processed_tracks.json` outside the container so it persists between Docker runs.

---

## 🛠️ Makefile Commands

A `Makefile` is included for common developer tasks:

```bash
make install        # Install production dependencies
make install-dev    # Install all dependencies + pre-commit hooks
make fmt            # Auto-format code with black + isort
make lint           # Run black, isort, flake8 checks
make test           # Run unit tests with coverage
make sync           # Run the sync locally (requires env vars)
make dry-run        # Preview sync without making changes
make since DATE=2025-01-01  # Sync songs liked since a date
make dedup          # Preview and remove duplicate YouTube videos
make tokens         # Run the token helper script
make clean          # Remove __pycache__, .pytest_cache, temp files
```

---

## 🧹 Bonus: Remove Duplicate Videos

If your playlist already has duplicate videos (from previous runs or manual additions), run:

```bash
# Preview what would be deleted (safe — no changes made)
python remove_duplicates.py --dry-run

# Actually delete duplicates
python remove_duplicates.py
```

Set these environment variables locally before running:

```bash
# Windows (Command Prompt)
set PLAYLIST_ID=your_playlist_id
set YOUTUBE_CLIENT_ID=your_client_id
set YOUTUBE_CLIENT_SECRET=your_client_secret
set YOUTUBE_REFRESH_TOKEN=your_refresh_token

# macOS / Linux
export PLAYLIST_ID=your_playlist_id
export YOUTUBE_CLIENT_ID=your_client_id
export YOUTUBE_CLIENT_SECRET=your_client_secret
export YOUTUBE_REFRESH_TOKEN=your_refresh_token
```

Or use the Makefile shortcut:

```bash
make dedup
```

---

## ⚙️ Customisation

All behaviour can be controlled via environment variables. Add them to your GitHub Actions Secrets or set them locally.

| Variable | Default | Description |
|----------|---------|-------------|
| `PROCESSED_FILE` | `processed_tracks.json` | Path to the state file |
| `SEARCH_SUFFIX` | `official audio` | Appended to YouTube search queries (try `lyrics`, `music video`, etc.) |
| `MAX_RETRIES` | `3` | How many times to retry on transient API errors |
| `RETRY_BASE_DELAY` | `2.0` | Base delay in seconds for exponential backoff |

**Change the sync schedule:**  
Edit `.github/workflows/sync.yml` and change the cron expression:

```yaml
on:
  schedule:
    - cron: "0 2 * * *"   # Daily at 02:00 UTC
    # - cron: "0 */6 * * *"  # Every 6 hours
    # - cron: "0 2 * * 1"    # Weekly on Mondays
```

Use **[crontab.guru](https://crontab.guru/)** to easily build cron expressions.

---

## 🔧 Troubleshooting

### ❌ `Missing required environment variable: SPOTIFY_CLIENT_ID`

**Cause:** One or more GitHub Secrets are missing or named incorrectly.  
**Fix:** Go to **Settings → Secrets and variables → Actions** and verify all 7 secrets are present with the exact names shown in [Step 5](#-step-5--add-github-secrets).

---

### ❌ `invalid_grant` or `Token has been expired or revoked`

**Cause:** Your refresh token has become invalid (this can happen if you revoke app access or change your Google password).  
**Fix:** Re-run `python scripts/get_tokens.py` locally to get a new refresh token, then update the corresponding GitHub Secret.

---

### ❌ `quota exceeded` / `The caller does not have permission`

**Cause:** You've hit the YouTube API's daily quota of 10,000 units.  
**Fix:** This is normal for large libraries. The script saves its progress automatically, so it will resume tomorrow without re-adding songs. If you see this consistently, check the [Google Cloud Console Quotas page](https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas) — you can request a quota increase for free.

---

### ❌ `Error 403: access_denied` during Google OAuth

**Cause:** Your Google account is not added as a Test User on the OAuth Consent Screen.  
**Fix:**
1. Go to **[Google Cloud Console](https://console.cloud.google.com/)** → your project.
2. **APIs & Services → OAuth consent screen**.
3. Scroll to **Test users** → Add your email → Save.
4. Re-run `python scripts/get_tokens.py`.

---

### ❌ Songs are being added but not to the right playlist

**Cause:** The `PLAYLIST_ID` secret is incorrect.  
**Fix:** Open your YouTube playlist in a browser. The URL will be:  
`https://www.youtube.com/playlist?list=PLxxxxxxxxxxxx`  
Copy everything after `list=` — that is your Playlist ID.

---

### ❌ The workflow runs but `processed_tracks.json` isn't being committed

**Cause:** The `contents: write` permission may be blocked by your organisation's settings.  
**Fix:** Check **Settings → Actions → General → Workflow permissions** in your repository and select **"Read and write permissions"**.

---

### ⚠️ Some songs aren't found on YouTube

The script tries multiple search strategies (`official music video` → `official audio` → `lyric video` → bare query) before giving up. If a song still isn't found (licensing restrictions, very rare tracks), it will be **marked as processed** (to prevent infinite retries) with a warning in the logs. You can customise the search query suffix via the `SEARCH_SUFFIX` environment variable.

---

## ❓ FAQ

**Q: Will this work with a free Spotify account?**  
A: Yes! The script only reads your Liked Songs, which is available with any Spotify account tier.

**Q: What happens if the same song is on YouTube under a different name?**  
A: The script uses multiple YouTube search strategies for the best match. Results are generally accurate for popular songs. For rare or regional tracks, you may need to add them manually.

**Q: Can I sync a Spotify playlist instead of Liked Songs?**  
A: The current version syncs Liked Songs. To sync a specific playlist, you'd need to modify `youtube.py` to call `sp.playlist_tracks(playlist_id)` instead of `sp.current_user_saved_tracks()`.

**Q: Will it re-sync songs I delete from YouTube?**  
A: No. `processed_tracks.json` tracks **Spotify IDs** that have been processed. Once a song is processed, it won't be re-added even if you delete it from YouTube. To re-sync a deleted song, remove its ID from `processed_tracks.json`.

**Q: Is there a risk of my tokens being exposed?**  
A: No, as long as you add them as **GitHub Secrets** (not as environment variables in the workflow file). Secrets are encrypted and never shown in logs.

**Q: How do I stop the sync?**  
A: Go to **Actions → 🎵 Spotify → YouTube Sync → ... → Disable workflow**. This pauses the scheduled runs without deleting anything.

**Q: Can I run this without Python installed locally?**  
A: Yes — use the [Docker image](#-docker-support). Build and run the container with your credentials in a `.env` file.

**Q: What does the `--since` flag do?**  
A: It filters your Spotify Liked Songs to only process tracks you liked **on or after** the given date. Useful for large libraries where you only want to catch up from a certain point.

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) first.

### How to contribute

1. **Fork** the repository
2. Create a feature branch: `git checkout -b feature/my-new-feature`
3. Install dev tools: `make install-dev`
4. Make your changes and add tests in `tests/`
5. Verify everything passes: `make lint && make test`
6. Open a **Pull Request** with a clear description

### Ideas for contributions

- [ ] Support syncing specific Spotify playlists (not just Liked Songs)
- [ ] Send a summary email/notification after each run
- [ ] Support multiple YouTube playlists (e.g. genre-based routing)
- [ ] Web UI for token setup (replace the CLI script)

---

## 🔒 Security

Please report security vulnerabilities responsibly via [SECURITY.md](SECURITY.md) — **do not** open a public GitHub issue.

---

## 📄 Changelog

See [CHANGELOG.md](CHANGELOG.md) for a full list of changes between versions.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

You're free to use, modify, and distribute this — personal or commercial. Attribution is appreciated but not required.

---

<div align="center">

Made with ❤️ for music lovers who live in both Spotify and YouTube.

**[⭐ Star this repo](../../stargazers)** if it saved you time!

</div>
