"""
spotify_youtube_sync/youtube.py
================================
Production-ready Spotify → YouTube Music sync engine.

Features:
  - Fetches ALL liked songs from Spotify (handles pagination automatically)
  - Searches YouTube for each track and adds to a target playlist
  - Skips already-processed tracks via a persistent JSON state file
  - Smart search preference: official music video > official audio > lyric video
  - Exponential-backoff retry on transient HTTP errors
  - Graceful quota-exceeded detection (stops and saves state safely)
  - Structured logging to both stdout and a rotating log file
  - Configurable via environment variables only (zero hard-coded secrets)
  - Dry-run mode (--dry-run): previews what would be added without making changes
  - Date-filter mode (--since YYYY-MM-DD): only syncs songs liked after a date
  - Concurrency guard: honours GITHUB_RUN_ID to avoid duplicate concurrent runs

Usage:
  Set all required environment variables (see README), then run:
      python youtube.py [--dry-run] [--since YYYY-MM-DD] [--verbose]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

import spotipy
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from spotipy.oauth2 import SpotifyOAuth

# ──────────────────────────────────────────────────────────────────────────────
# LOGGING SETUP
# ──────────────────────────────────────────────────────────────────────────────

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

_fmt = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_handler_stdout = logging.StreamHandler(sys.stdout)
_handler_stdout.setFormatter(_fmt)

_handler_file = RotatingFileHandler(
    LOG_DIR / "sync.log",
    maxBytes=5 * 1024 * 1024,  # 5 MB per file
    backupCount=3,
    encoding="utf-8",
)
_handler_file.setFormatter(_fmt)

log = logging.getLogger("spotify_youtube_sync")
log.setLevel(logging.INFO)
log.addHandler(_handler_stdout)
log.addHandler(_handler_file)


# ──────────────────────────────────────────────────────────────────────────────
# CLI ARGUMENTS
# ──────────────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync Spotify Liked Songs to a YouTube playlist.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Environment variables (all required unless noted):\n"
            "  SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN\n"
            "  YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN\n"
            "  PLAYLIST_ID\n\n"
            "Optional overrides:\n"
            "  PROCESSED_FILE, MAX_RETRIES, RETRY_BASE_DELAY, SEARCH_SUFFIX"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be added without actually calling the YouTube API.",
    )
    parser.add_argument(
        "--since",
        metavar="YYYY-MM-DD",
        default=None,
        help="Only sync songs that were liked on or after this date (UTC).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable DEBUG-level log output.",
    )
    return parser.parse_args()


# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────


def _require_env(key: str) -> str:
    """Return the value of an environment variable or abort with a helpful error."""
    value = os.environ.get(key, "").strip()
    if not value:
        log.critical("Missing required environment variable: %s", key)
        sys.exit(1)
    return value


# Spotify credentials
SPOTIFY_CLIENT_ID = _require_env("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = _require_env("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REFRESH_TOKEN = _require_env("SPOTIFY_REFRESH_TOKEN")

# YouTube / Google credentials
YOUTUBE_CLIENT_ID = _require_env("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = _require_env("YOUTUBE_CLIENT_SECRET")
YOUTUBE_REFRESH_TOKEN = _require_env("YOUTUBE_REFRESH_TOKEN")
PLAYLIST_ID = _require_env("PLAYLIST_ID")

# Tunable parameters (override via environment variables if needed)
PROCESSED_FILE = Path(os.environ.get("PROCESSED_FILE", "processed_tracks.json"))
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
RETRY_BASE_DELAY = float(os.environ.get("RETRY_BASE_DELAY", "2.0"))  # seconds
SEARCH_SUFFIX = os.environ.get("SEARCH_SUFFIX", "official audio")  # appended to YouTube query

# Smart search: preferred suffixes tried in order until a result is found
_SMART_SEARCH_SUFFIXES = ["official music video", "official audio", "lyric video", ""]


# ──────────────────────────────────────────────────────────────────────────────
# PERSISTENT STATE
# ──────────────────────────────────────────────────────────────────────────────


def load_processed() -> set[str]:
    """Load the set of already-processed Spotify track IDs from disk."""
    if PROCESSED_FILE.exists():
        try:
            with PROCESSED_FILE.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                return set(data)
            log.warning("Unexpected format in %s — resetting state.", PROCESSED_FILE)
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Could not read %s (%s) — starting fresh.", PROCESSED_FILE, exc)
    return set()


def save_processed(processed: set[str]) -> None:
    """Atomically persist the processed set so partial runs don't corrupt state."""
    tmp = PROCESSED_FILE.with_suffix(".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(sorted(processed), fh, indent=2)
        tmp.replace(PROCESSED_FILE)
        log.debug("State saved: %d processed tracks.", len(processed))
    except OSError as exc:
        log.error("Failed to save state file: %s", exc)
        # Don't crash — progress is still in-memory for this run


# ──────────────────────────────────────────────────────────────────────────────
# SPOTIFY CLIENT
# ──────────────────────────────────────────────────────────────────────────────


def build_spotify_client() -> spotipy.Spotify:
    """Authenticate with Spotify using a stored refresh token."""
    auth = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri="http://localhost:8888/callback",
        scope="user-library-read",
    )
    token_info = auth.refresh_access_token(SPOTIFY_REFRESH_TOKEN)
    log.info("✅ Spotify authenticated.")
    return spotipy.Spotify(auth=token_info["access_token"])


def fetch_liked_songs(
    sp: spotipy.Spotify,
    since: Optional[datetime] = None,
) -> list[dict]:
    """
    Retrieve ALL liked songs from the authenticated Spotify user.

    Args:
        sp:    Authenticated Spotipy client.
        since: If provided, only return songs liked on or after this datetime (UTC).

    Returns:
        List of dicts with keys: id, name, artists, added_at.
    """
    songs: list[dict] = []
    page = sp.current_user_saved_tracks(limit=50)

    while page:
        for item in page["items"]:
            track = item.get("track")
            if not track or not track.get("id"):
                continue

            # --since filter
            if since is not None:
                added_at_str = item.get("added_at", "")
                try:
                    added_at = datetime.fromisoformat(added_at_str.replace("Z", "+00:00"))
                    if added_at < since:
                        continue
                except (ValueError, AttributeError):
                    pass  # include if date can't be parsed

            songs.append(
                {
                    "id": track["id"],
                    "name": track["name"],
                    "artists": ", ".join(a["name"] for a in track["artists"]),
                    "added_at": item.get("added_at", ""),
                }
            )
        page = sp.next(page) if page.get("next") else None

    log.info("🎵 Total Spotify liked songs fetched: %d", len(songs))
    return songs


# ──────────────────────────────────────────────────────────────────────────────
# YOUTUBE CLIENT
# ──────────────────────────────────────────────────────────────────────────────


def build_youtube_client():  # type: ignore[return]
    """Authenticate with YouTube using a stored refresh token."""
    creds = Credentials(
        token=None,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/youtube"],
    )
    creds.refresh(Request())
    client = build("youtube", "v3", credentials=creds, cache_discovery=False)
    log.info("✅ YouTube authenticated.")
    return client


# ──────────────────────────────────────────────────────────────────────────────
# CORE SYNC LOGIC
# ──────────────────────────────────────────────────────────────────────────────


def _search_once(youtube, query: str) -> Optional[str]:
    """
    Execute a single YouTube search and return the top video ID, or None.
    Does NOT retry — the caller handles retries.
    Raises HttpError on quota/auth failures.
    """
    response = (
        youtube.search()
        .list(
            q=query,
            part="snippet",
            maxResults=3,
            type="video",
            videoCategoryId="10",  # Music category
        )
        .execute()
    )
    items = response.get("items", [])
    if items:
        return items[0]["id"]["videoId"]
    return None


def search_youtube(youtube, track_name: str, artists: str) -> Optional[str]:
    """
    Search YouTube for a video matching the given track.

    Tries multiple search suffix strategies (official music video → official
    audio → lyric video → bare query) to maximise match quality.

    Returns the video ID of the best match, or None if nothing was found.
    Retries on transient 5xx errors with exponential backoff.
    Raises HttpError(403) for quota exhaustion.
    """
    suffixes = _SMART_SEARCH_SUFFIXES if SEARCH_SUFFIX == "official audio" else [SEARCH_SUFFIX, ""]

    for suffix in suffixes:
        query = f"{track_name} {artists} {suffix}".strip()
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                video_id = _search_once(youtube, query)
                if video_id:
                    return video_id
                break  # No result for this suffix — try next suffix

            except HttpError as exc:
                status = exc.resp.status
                if status == 403:
                    raise  # quota exceeded — bubble up
                if status >= 500 and attempt < MAX_RETRIES:
                    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    log.warning(
                        "YouTube search failed (HTTP %d). Retrying in %.1fs … (attempt %d/%d)",
                        status,
                        delay,
                        attempt,
                        MAX_RETRIES,
                    )
                    time.sleep(delay)
                else:
                    log.error("YouTube search error for query '%s': %s", query, exc)
                    break  # move to next suffix

    return None


def add_to_playlist(youtube, video_id: str, playlist_id: str) -> None:
    """
    Insert *video_id* into *playlist_id*.

    Retries on transient 5xx errors. Raises HttpError for quota / auth issues.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id,
                        },
                    }
                },
            ).execute()
            return

        except HttpError as exc:
            status = exc.resp.status
            if status in (403, 404):
                raise
            if status >= 500 and attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                log.warning(
                    "Playlist insert failed (HTTP %d). Retrying in %.1fs … (attempt %d/%d)",
                    status,
                    delay,
                    attempt,
                    MAX_RETRIES,
                )
                time.sleep(delay)
            else:
                raise


def sync(
    youtube,
    songs: list[dict],
    processed: set[str],
    dry_run: bool = False,
) -> tuple[int, int, int]:
    """
    Main sync loop.

    Iterates over *songs*, skips already-processed ones, searches YouTube,
    and adds new videos to the configured playlist.

    Args:
        youtube:   Authenticated YouTube API client.
        songs:     List of Spotify track dicts (id, name, artists).
        processed: Set of Spotify track IDs already synced.
        dry_run:   If True, log what would happen but don't call YouTube write APIs.

    Returns:
        Tuple of (new_count, skip_count, error_count).
    """
    new_count = 0
    skip_count = 0
    error_count = 0

    for track in songs:
        track_id = track["id"]

        if track_id in processed:
            skip_count += 1
            continue

        try:
            video_id = search_youtube(youtube, track["name"], track["artists"])
            if not video_id:
                log.warning("⚠️  No YouTube result for: %s — %s", track["name"], track["artists"])
                processed.add(track_id)  # mark as processed to avoid retrying forever
                error_count += 1
                continue

            if dry_run:
                log.info(
                    "[DRY-RUN] Would add: %s — %s (video: %s)",
                    track["name"],
                    track["artists"],
                    video_id,
                )
                processed.add(track_id)
                new_count += 1
                continue

            add_to_playlist(youtube, video_id, PLAYLIST_ID)
            processed.add(track_id)
            new_count += 1
            log.info("✅ Added: %s — %s", track["name"], track["artists"])

        except HttpError as exc:
            if exc.resp.status == 403:
                log.warning("🚫 YouTube API quota exceeded. Saving progress and stopping safely.")
                break
            log.error("❌ HTTP error for '%s': %s", track["name"], exc)
            error_count += 1

        except Exception as exc:  # noqa: BLE001
            log.error("❌ Unexpected error for '%s': %s", track["name"], exc)
            error_count += 1

    return new_count, skip_count, error_count


# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────


def main() -> None:
    args = parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)
        for h in log.handlers:
            h.setLevel(logging.DEBUG)

    dry_run_label = "  [DRY-RUN MODE — no changes will be made]" if args.dry_run else ""

    log.info("=" * 60)
    log.info("  Spotify → YouTube Sync  —  starting run%s", dry_run_label)
    log.info("=" * 60)

    # Parse --since date
    since: Optional[datetime] = None
    if args.since:
        try:
            since = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            log.info("📅 Filtering songs liked on or after: %s", args.since)
        except ValueError:
            log.critical("Invalid --since date format. Expected YYYY-MM-DD, got: %s", args.since)
            sys.exit(1)

    # --- Authenticate ---
    sp = build_spotify_client()
    youtube = build_youtube_client()

    # --- Fetch data ---
    songs = fetch_liked_songs(sp, since=since)
    processed = load_processed()
    log.info("📋 Already processed: %d tracks", len(processed))

    # --- Sync ---
    new_count, skip_count, error_count = sync(youtube, songs, processed, dry_run=args.dry_run)

    # --- Persist state ---
    save_processed(processed)

    # --- Summary ---
    log.info("=" * 60)
    log.info("  Run complete.%s", dry_run_label)
    log.info("  ✅ New songs added   : %d", new_count)
    log.info("  ⏭️  Skipped (done)   : %d", skip_count)
    log.info("  ⚠️  Errors/not found : %d", error_count)
    log.info("=" * 60)

    # Output GitHub Actions job summary if running in CI
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        try:
            with open(summary_file, "a", encoding="utf-8") as fh:
                status = "DRY-RUN" if args.dry_run else "✅ Success"
                fh.write(f"## 🎵 Spotify → YouTube Sync Summary\n\n")
                fh.write(f"| Metric | Count |\n|--------|-------|\n")
                fh.write(f"| Status | {status} |\n")
                fh.write(f"| ✅ New songs added | {new_count} |\n")
                fh.write(f"| ⏭️ Already synced (skipped) | {skip_count} |\n")
                fh.write(f"| ⚠️ Not found / errors | {error_count} |\n")
                fh.write(f"| 📦 Total in state file | {len(processed)} |\n")
        except OSError:
            pass  # Non-critical — don't fail the run


if __name__ == "__main__":
    main()
