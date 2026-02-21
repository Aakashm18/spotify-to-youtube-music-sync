"""
spotify_youtube_sync/remove_duplicates.py
==========================================
Production-ready script to detect and remove duplicate videos in a YouTube
playlist.

It keeps the **first** occurrence of every video and deletes all subsequent
duplicates in paginated batches, so playlists of any size are handled safely.

Usage:
  Set the required environment variables (see README), then run:
      python remove_duplicates.py

  Use --dry-run to preview what would be deleted without making any changes:
      python remove_duplicates.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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
    LOG_DIR / "dedup.log",
    maxBytes=2 * 1024 * 1024,
    backupCount=2,
    encoding="utf-8",
)
_handler_file.setFormatter(_fmt)

log = logging.getLogger("remove_duplicates")
log.setLevel(logging.INFO)
log.addHandler(_handler_stdout)
log.addHandler(_handler_file)


# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────


def _require_env(key: str) -> str:
    value = os.environ.get(key, "").strip()
    if not value:
        log.critical("Missing required environment variable: %s", key)
        sys.exit(1)
    return value


PLAYLIST_ID = _require_env("PLAYLIST_ID")
YOUTUBE_CLIENT_ID = _require_env("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = _require_env("YOUTUBE_CLIENT_SECRET")
YOUTUBE_REFRESH_TOKEN = _require_env("YOUTUBE_REFRESH_TOKEN")

MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
RETRY_BASE_DELAY = float(os.environ.get("RETRY_BASE_DELAY", "2.0"))


# ──────────────────────────────────────────────────────────────────────────────
# YOUTUBE CLIENT
# ──────────────────────────────────────────────────────────────────────────────


def build_youtube_client():
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
# CORE LOGIC
# ──────────────────────────────────────────────────────────────────────────────


def fetch_all_playlist_items(youtube, playlist_id: str) -> list[dict]:
    """
    Retrieve every playlist item (all pages) for *playlist_id*.

    Each element has:
        playlist_item_id : the unique ID of the playlist entry (used for deletion)
        video_id         : the YouTube video ID
        title            : the video title (for logging)
        position         : zero-based position in the playlist
    """
    items: list[dict] = []
    page_token = None

    while True:
        try:
            response = (
                youtube.playlistItems()
                .list(
                    part="snippet",
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=page_token,
                )
                .execute()
            )
        except HttpError as exc:
            log.error("Failed to fetch playlist items: %s", exc)
            sys.exit(1)

        for raw in response.get("items", []):
            snippet = raw["snippet"]
            items.append(
                {
                    "playlist_item_id": raw["id"],
                    "video_id": snippet["resourceId"]["videoId"],
                    "title": snippet.get("title", "Unknown"),
                    "position": snippet.get("position", -1),
                }
            )

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    log.info("📦 Total playlist items fetched: %d", len(items))
    return items


def find_duplicates(items: list[dict]) -> list[dict]:
    """
    Return a list of duplicate playlist entries (all but the first occurrence).

    Duplicates are identified by *video_id*; the first occurrence is kept.
    """
    seen: set[str] = set()
    duplicates: list[dict] = []

    for item in items:
        vid = item["video_id"]
        if vid in seen:
            duplicates.append(item)
        else:
            seen.add(vid)

    log.info("🔁 Duplicate entries found: %d", len(duplicates))
    return duplicates


def delete_playlist_item(youtube, playlist_item_id: str) -> None:
    """Delete a playlist entry by its playlist item ID (with retry logic)."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            youtube.playlistItems().delete(id=playlist_item_id).execute()
            return
        except HttpError as exc:
            status = exc.resp.status
            if status in (403, 404):
                raise
            if status >= 500 and attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                log.warning("Delete failed (%d). Retrying in %.1fs …", status, delay)
                time.sleep(delay)
            else:
                raise


def remove_duplicates(youtube, duplicates: list[dict], dry_run: bool) -> tuple[int, int]:
    """
    Remove all *duplicates* from the playlist.

    Returns (deleted_count, error_count).
    """
    deleted = 0
    errors = 0

    for dup in duplicates:
        title = dup["title"]
        pid = dup["playlist_item_id"]

        if dry_run:
            log.info("[DRY-RUN] Would delete: '%s' (item_id=%s)", title, pid)
            deleted += 1
            continue

        try:
            delete_playlist_item(youtube, pid)
            log.info("🗑️  Removed duplicate: '%s' (item_id=%s)", title, pid)
            deleted += 1
        except HttpError as exc:
            log.error("❌ Failed to delete '%s' (item_id=%s): %s", title, pid, exc)
            errors += 1
        except Exception as exc:  # noqa: BLE001
            log.error("❌ Unexpected error deleting '%s': %s", title, exc)
            errors += 1

    return deleted, errors


# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Remove duplicate videos from a YouTube playlist.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview duplicates to be removed without deleting anything.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dry_run = args.dry_run

    log.info("=" * 60)
    log.info("  YouTube Playlist Deduplicator%s", "  [DRY-RUN]" if dry_run else "")
    log.info("=" * 60)

    youtube = build_youtube_client()
    items = fetch_all_playlist_items(youtube, PLAYLIST_ID)
    duplicates = find_duplicates(items)

    if not duplicates:
        log.info("🎉 No duplicates found. Your playlist is clean!")
        return

    deleted, errors = remove_duplicates(youtube, duplicates, dry_run)

    log.info("=" * 60)
    log.info("  Deduplication %s.", "preview complete" if dry_run else "complete")
    log.info("  %s : %d", "Would remove" if dry_run else "✅ Removed", deleted)
    log.info("  ❌ Errors      : %d", errors)
    log.info("=" * 60)


if __name__ == "__main__":
    main()
