"""
tests/test_sync.py
==================
Unit tests for the core youtube.py sync logic.

These tests use mocking so no real API calls are made.
Run with:  pytest tests/ -v
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── We patch env vars before importing youtube, because the module
# reads them at import time via _require_env(). ─────────────────────────────
_FAKE_ENV = {
    "SPOTIFY_CLIENT_ID": "fake-spotify-client",
    "SPOTIFY_CLIENT_SECRET": "fake-spotify-secret",
    "SPOTIFY_REFRESH_TOKEN": "fake-spotify-refresh",
    "YOUTUBE_CLIENT_ID": "fake-yt-client",
    "YOUTUBE_CLIENT_SECRET": "fake-yt-secret",
    "YOUTUBE_REFRESH_TOKEN": "fake-yt-refresh",
    "PLAYLIST_ID": "PLfakeplaylistid",
}


@pytest.fixture(autouse=True)
def patch_env(monkeypatch):
    """Ensure all required env vars are set for every test."""
    for k, v in _FAKE_ENV.items():
        monkeypatch.setenv(k, v)


# Import after env vars are patched
with patch.dict("os.environ", _FAKE_ENV):
    import youtube as yt


# ──────────────────────────────────────────────────────────────────────────────
# load_processed / save_processed
# ──────────────────────────────────────────────────────────────────────────────


class TestLoadProcessed:
    def test_returns_empty_set_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(yt, "PROCESSED_FILE", tmp_path / "nonexistent.json")
        result = yt.load_processed()
        assert result == set()

    def test_loads_valid_json_list(self, tmp_path, monkeypatch):
        pf = tmp_path / "tracks.json"
        pf.write_text(json.dumps(["id1", "id2"]), encoding="utf-8")
        monkeypatch.setattr(yt, "PROCESSED_FILE", pf)
        result = yt.load_processed()
        assert result == {"id1", "id2"}

    def test_returns_empty_set_on_corrupt_json(self, tmp_path, monkeypatch):
        pf = tmp_path / "tracks.json"
        pf.write_text("not-valid-json", encoding="utf-8")
        monkeypatch.setattr(yt, "PROCESSED_FILE", pf)
        result = yt.load_processed()
        assert result == set()

    def test_returns_empty_set_on_non_list_data(self, tmp_path, monkeypatch):
        pf = tmp_path / "tracks.json"
        pf.write_text(json.dumps({"key": "value"}), encoding="utf-8")
        monkeypatch.setattr(yt, "PROCESSED_FILE", pf)
        result = yt.load_processed()
        assert result == set()


class TestSaveProcessed:
    def test_saves_sorted_json(self, tmp_path, monkeypatch):
        pf = tmp_path / "tracks.json"
        monkeypatch.setattr(yt, "PROCESSED_FILE", pf)
        yt.save_processed({"c", "a", "b"})
        data = json.loads(pf.read_text(encoding="utf-8"))
        assert data == ["a", "b", "c"]

    def test_atomic_write_removes_tmp(self, tmp_path, monkeypatch):
        pf = tmp_path / "tracks.json"
        monkeypatch.setattr(yt, "PROCESSED_FILE", pf)
        yt.save_processed({"x"})
        assert not (tmp_path / "tracks.tmp").exists()


# ──────────────────────────────────────────────────────────────────────────────
# sync() — the main loop
# ──────────────────────────────────────────────────────────────────────────────


def _make_songs(n: int) -> list[dict]:
    return [{"id": f"id{i}", "name": f"Song {i}", "artists": f"Artist {i}"} for i in range(n)]


class TestSync:
    def _youtube(self):
        return MagicMock()

    def test_skips_already_processed_tracks(self):
        songs = _make_songs(3)
        processed = {"id0", "id1"}
        with (
            patch.object(yt, "search_youtube", return_value="vid1") as mock_search,
            patch.object(yt, "add_to_playlist") as mock_add,
        ):
            new, skipped, errors = yt.sync(self._youtube(), songs, processed)
        assert skipped == 2
        assert new == 1
        assert mock_search.call_count == 1
        assert mock_add.call_count == 1

    def test_dry_run_does_not_call_add_to_playlist(self):
        songs = _make_songs(2)
        processed: set[str] = set()
        with (
            patch.object(yt, "search_youtube", return_value="vid_abc"),
            patch.object(yt, "add_to_playlist") as mock_add,
        ):
            new, skipped, errors = yt.sync(self._youtube(), songs, processed, dry_run=True)
        mock_add.assert_not_called()
        assert new == 2

    def test_no_youtube_result_increments_errors(self):
        songs = _make_songs(1)
        processed: set[str] = set()
        with patch.object(yt, "search_youtube", return_value=None):
            new, skipped, errors = yt.sync(self._youtube(), songs, processed)
        assert new == 0
        assert errors == 1
        # Track should still be marked processed to avoid retrying forever
        assert "id0" in processed

    def test_quota_exceeded_breaks_loop_safely(self):
        from googleapiclient.errors import HttpError

        songs = _make_songs(3)
        processed: set[str] = set()
        mock_resp = MagicMock()
        mock_resp.status = 403

        def raise_quota(*args, **kwargs):
            raise HttpError(resp=mock_resp, content=b"quotaExceeded")

        with patch.object(yt, "search_youtube", side_effect=raise_quota):
            new, skipped, errors = yt.sync(self._youtube(), songs, processed)

        # Should stop after first 403, not process all 3
        assert new == 0

    def test_empty_songs_list(self):
        processed: set[str] = set()
        with patch.object(yt, "search_youtube") as mock_search:
            new, skipped, errors = yt.sync(self._youtube(), [], processed)
        assert new == 0
        assert skipped == 0
        assert errors == 0
        mock_search.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────────
# fetch_liked_songs — date filter
# ──────────────────────────────────────────────────────────────────────────────


class TestFetchLikedSongs:
    def _make_page(self, tracks: list[dict]) -> dict:
        return {
            "items": [
                {
                    "track": {"id": t["id"], "name": t["name"], "artists": [{"name": t["artist"]}]},
                    "added_at": t["added_at"],
                }
                for t in tracks
            ],
            "next": None,
        }

    def test_since_filter_excludes_older_songs(self):
        from datetime import datetime, timezone

        mock_sp = MagicMock()
        mock_sp.current_user_saved_tracks.return_value = self._make_page(
            [
                {
                    "id": "old1",
                    "name": "Old Song",
                    "artist": "X",
                    "added_at": "2024-01-01T00:00:00Z",
                },
                {
                    "id": "new1",
                    "name": "New Song",
                    "artist": "Y",
                    "added_at": "2025-06-01T00:00:00Z",
                },
            ]
        )
        mock_sp.next.return_value = None

        since = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result = yt.fetch_liked_songs(mock_sp, since=since)

        ids = [s["id"] for s in result]
        assert "old1" not in ids
        assert "new1" in ids
