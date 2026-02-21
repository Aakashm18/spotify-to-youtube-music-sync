"""
tests/test_dedup.py
===================
Unit tests for the remove_duplicates.py script.

Run with:  pytest tests/ -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

_FAKE_ENV = {
    "PLAYLIST_ID": "PLfakeplaylistid",
    "YOUTUBE_CLIENT_ID": "fake-yt-client",
    "YOUTUBE_CLIENT_SECRET": "fake-yt-secret",
    "YOUTUBE_REFRESH_TOKEN": "fake-yt-refresh",
}


@pytest.fixture(autouse=True)
def patch_env(monkeypatch):
    for k, v in _FAKE_ENV.items():
        monkeypatch.setenv(k, v)


with patch.dict("os.environ", _FAKE_ENV):
    import remove_duplicates as rd


# ──────────────────────────────────────────────────────────────────────────────
# find_duplicates
# ──────────────────────────────────────────────────────────────────────────────


class TestFindDuplicates:
    def test_no_duplicates(self):
        items = [
            {"playlist_item_id": "pi1", "video_id": "v1", "title": "Song 1", "position": 0},
            {"playlist_item_id": "pi2", "video_id": "v2", "title": "Song 2", "position": 1},
        ]
        dups = rd.find_duplicates(items)
        assert dups == []

    def test_detects_single_duplicate(self):
        items = [
            {"playlist_item_id": "pi1", "video_id": "v1", "title": "Song 1", "position": 0},
            {"playlist_item_id": "pi2", "video_id": "v1", "title": "Song 1", "position": 1},  # dup
        ]
        dups = rd.find_duplicates(items)
        assert len(dups) == 1
        assert dups[0]["playlist_item_id"] == "pi2"

    def test_keeps_first_occurrence(self):
        items = [
            {"playlist_item_id": "pi1", "video_id": "v1", "title": "Song 1", "position": 0},
            {"playlist_item_id": "pi2", "video_id": "v1", "title": "Song 1", "position": 1},
            {"playlist_item_id": "pi3", "video_id": "v1", "title": "Song 1", "position": 2},
        ]
        dups = rd.find_duplicates(items)
        assert len(dups) == 2
        pi_ids = {d["playlist_item_id"] for d in dups}
        assert "pi1" not in pi_ids  # first occurrence kept

    def test_empty_list(self):
        assert rd.find_duplicates([]) == []

    def test_mixed_videos(self):
        items = [
            {"playlist_item_id": "pi1", "video_id": "v1", "title": "Song A", "position": 0},
            {"playlist_item_id": "pi2", "video_id": "v2", "title": "Song B", "position": 1},
            {"playlist_item_id": "pi3", "video_id": "v1", "title": "Song A", "position": 2},
            {"playlist_item_id": "pi4", "video_id": "v3", "title": "Song C", "position": 3},
            {"playlist_item_id": "pi5", "video_id": "v2", "title": "Song B", "position": 4},
        ]
        dups = rd.find_duplicates(items)
        assert len(dups) == 2
        dup_pis = {d["playlist_item_id"] for d in dups}
        assert dup_pis == {"pi3", "pi5"}


# ──────────────────────────────────────────────────────────────────────────────
# remove_duplicates
# ──────────────────────────────────────────────────────────────────────────────


class TestRemoveDuplicates:
    def _dup(self, pid: str, title: str = "Song") -> dict:
        return {"playlist_item_id": pid, "video_id": "v1", "title": title, "position": 1}

    def test_dry_run_does_not_delete(self):
        youtube = MagicMock()
        dups = [self._dup("pi1"), self._dup("pi2")]
        with patch.object(rd, "delete_playlist_item") as mock_del:
            deleted, errors = rd.remove_duplicates(youtube, dups, dry_run=True)
        mock_del.assert_not_called()
        assert deleted == 2
        assert errors == 0

    def test_deletes_all_duplicates(self):
        youtube = MagicMock()
        dups = [self._dup("pi1"), self._dup("pi2")]
        with patch.object(rd, "delete_playlist_item") as mock_del:
            deleted, errors = rd.remove_duplicates(youtube, dups, dry_run=False)
        assert mock_del.call_count == 2
        assert deleted == 2
        assert errors == 0

    def test_error_is_counted_not_raised(self):
        from googleapiclient.errors import HttpError

        youtube = MagicMock()
        dups = [self._dup("pi1")]
        mock_resp = MagicMock()
        mock_resp.status = 500

        with patch.object(rd, "delete_playlist_item", side_effect=HttpError(mock_resp, b"err")):
            deleted, errors = rd.remove_duplicates(youtube, dups, dry_run=False)
        assert errors == 1
        assert deleted == 0

    def test_empty_duplicates_list(self):
        youtube = MagicMock()
        deleted, errors = rd.remove_duplicates(youtube, [], dry_run=False)
        assert deleted == 0
        assert errors == 0
