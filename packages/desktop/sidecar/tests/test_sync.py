"""Tests for sidecar sync orchestration."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from photo_score.storage.cache import Cache
from photo_score.storage.models import ImageMetadata, NormalizedAttributes


@pytest.fixture
def temp_cache():
    """Create a cache with a temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_cache.db"
        yield Cache(db_path)


@pytest.fixture
def temp_settings(tmp_path):
    """Provide a temporary settings file."""
    settings_file = tmp_path / "settings.json"
    settings_file.write_text("{}")
    return settings_file


def _make_attrs(image_id, scored_at=None, composition=0.5):
    """Helper to create NormalizedAttributes."""
    return NormalizedAttributes(
        image_id=image_id,
        composition=composition,
        subject_strength=0.5,
        visual_appeal=0.5,
        sharpness=0.5,
        exposure_balance=0.5,
        noise_level=0.5,
        scored_at=scored_at,
    )


class TestSyncOrchestration:
    """Tests for start_sync handler orchestration."""

    @pytest.mark.asyncio
    async def test_push_reads_unsynced_and_sends(self, temp_cache, tmp_path):
        """Should read unsynced attributes and push them."""
        now = datetime.now(timezone.utc)
        attrs = _make_attrs("img1", scored_at=now)
        temp_cache.store_attributes(attrs)

        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{}")

        mock_push = AsyncMock(return_value={"synced": 1, "conflicts": []})
        mock_pull = AsyncMock(return_value={"attributes": [], "next_cursor": None})

        with (
            patch("handlers.sync.Cache", return_value=temp_cache),
            patch("handlers.sync.SETTINGS_FILE", settings_file),
            patch("handlers.sync.cloud_client") as mock_client,
        ):
            mock_client.push_attributes = mock_push
            mock_client.pull_attributes = mock_pull

            from handlers.sync import start_sync, SyncRequest

            result = await start_sync(SyncRequest(auth_token="test"))

        assert result.synced == 1
        mock_push.assert_called_once()
        payload = mock_push.call_args[0][0]
        assert len(payload) == 1
        assert payload[0]["image_id"] == "img1"

    @pytest.mark.asyncio
    async def test_push_batches_correctly(self, temp_cache, tmp_path):
        """Should batch into groups of 500."""
        now = datetime.now(timezone.utc)
        # Create 600 unsynced records
        for i in range(600):
            temp_cache.store_attributes(_make_attrs(f"img_{i}", scored_at=now))

        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{}")

        mock_push = AsyncMock(return_value={"synced": 500, "conflicts": []})
        mock_pull = AsyncMock(return_value={"attributes": [], "next_cursor": None})

        with (
            patch("handlers.sync.Cache", return_value=temp_cache),
            patch("handlers.sync.SETTINGS_FILE", settings_file),
            patch("handlers.sync.cloud_client") as mock_client,
        ):
            # Return different counts for each batch
            mock_client.push_attributes = AsyncMock(
                side_effect=[
                    {"synced": 500, "conflicts": []},
                    {"synced": 100, "conflicts": []},
                ]
            )
            mock_client.pull_attributes = mock_pull

            from handlers.sync import start_sync, SyncRequest

            result = await start_sync(SyncRequest(auth_token="test"))

        assert mock_client.push_attributes.call_count == 2
        # First batch has 500, second has 100
        first_batch = mock_client.push_attributes.call_args_list[0][0][0]
        second_batch = mock_client.push_attributes.call_args_list[1][0][0]
        assert len(first_batch) == 500
        assert len(second_batch) == 100

    @pytest.mark.asyncio
    async def test_push_includes_serialized_metadata(self, temp_cache, tmp_path):
        """Should include metadata when available."""
        now = datetime.now(timezone.utc)
        attrs = _make_attrs("img_meta", scored_at=now)
        temp_cache.store_attributes(attrs)
        temp_cache.store_metadata(
            "img_meta",
            ImageMetadata(description="A sunset", location_name="Beach"),
        )

        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{}")

        mock_push = AsyncMock(return_value={"synced": 1, "conflicts": []})
        mock_pull = AsyncMock(return_value={"attributes": [], "next_cursor": None})

        with (
            patch("handlers.sync.Cache", return_value=temp_cache),
            patch("handlers.sync.SETTINGS_FILE", settings_file),
            patch("handlers.sync.cloud_client") as mock_client,
        ):
            mock_client.push_attributes = mock_push
            mock_client.pull_attributes = mock_pull

            from handlers.sync import start_sync, SyncRequest

            await start_sync(SyncRequest(auth_token="test"))

        payload = mock_push.call_args[0][0]
        assert payload[0]["metadata"]["description"] == "A sunset"
        assert payload[0]["metadata"]["location_name"] == "Beach"

    @pytest.mark.asyncio
    async def test_push_utc_timestamps(self, temp_cache, tmp_path):
        """scored_at should be serialized as UTC ISO-8601."""
        now = datetime.now(timezone.utc)
        attrs = _make_attrs("img_ts", scored_at=now)
        temp_cache.store_attributes(attrs)

        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{}")

        mock_push = AsyncMock(return_value={"synced": 1, "conflicts": []})
        mock_pull = AsyncMock(return_value={"attributes": [], "next_cursor": None})

        with (
            patch("handlers.sync.Cache", return_value=temp_cache),
            patch("handlers.sync.SETTINGS_FILE", settings_file),
            patch("handlers.sync.cloud_client") as mock_client,
        ):
            mock_client.push_attributes = mock_push
            mock_client.pull_attributes = mock_pull

            from handlers.sync import start_sync, SyncRequest

            await start_sync(SyncRequest(auth_token="test"))

        payload = mock_push.call_args[0][0]
        assert payload[0]["scored_at"] == now.isoformat()
        assert "+00:00" in payload[0]["scored_at"]

    @pytest.mark.asyncio
    async def test_conflict_overwrites_local(self, temp_cache, tmp_path):
        """On conflict, should overwrite local with cloud_record."""
        now = datetime.now(timezone.utc)
        attrs = _make_attrs("conflict_img", scored_at=now, composition=0.3)
        temp_cache.store_attributes(attrs)

        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{}")

        cloud_attrs = {
            "composition": 0.9,
            "subject_strength": 0.8,
            "visual_appeal": 0.7,
            "sharpness": 0.6,
            "exposure_balance": 0.5,
            "noise_level": 0.4,
        }
        conflict_response = {
            "synced": 0,
            "conflicts": [
                {
                    "image_id": "conflict_img",
                    "reason": "cloud_newer_or_equal",
                    "cloud_record": {
                        "attributes": cloud_attrs,
                        "scored_at": now.isoformat(),
                        "metadata": {"description": "Cloud version"},
                    },
                }
            ],
        }

        mock_push = AsyncMock(return_value=conflict_response)
        mock_pull = AsyncMock(return_value={"attributes": [], "next_cursor": None})

        with (
            patch("handlers.sync.Cache", return_value=temp_cache),
            patch("handlers.sync.SETTINGS_FILE", settings_file),
            patch("handlers.sync.cloud_client") as mock_client,
        ):
            mock_client.push_attributes = mock_push
            mock_client.pull_attributes = mock_pull

            from handlers.sync import start_sync, SyncRequest

            await start_sync(SyncRequest(auth_token="test"))

        # Verify local was overwritten
        local = temp_cache.get_attributes("conflict_img")
        assert local.composition == 0.9
        # Verify metadata was stored
        meta = temp_cache.get_metadata("conflict_img")
        assert meta.description == "Cloud version"

    @pytest.mark.asyncio
    async def test_reconciled_rows_not_re_uploaded(self, temp_cache, tmp_path):
        """After conflict resolution, rows should be marked synced and not re-uploaded."""
        now = datetime.now(timezone.utc)
        attrs = _make_attrs("reconciled", scored_at=now)
        temp_cache.store_attributes(attrs)

        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{}")

        cloud_attrs = {
            "composition": 0.9,
            "subject_strength": 0.5,
            "visual_appeal": 0.5,
            "sharpness": 0.5,
            "exposure_balance": 0.5,
            "noise_level": 0.5,
        }
        conflict_response = {
            "synced": 0,
            "conflicts": [
                {
                    "image_id": "reconciled",
                    "reason": "cloud_newer_or_equal",
                    "cloud_record": {
                        "attributes": cloud_attrs,
                        "scored_at": now.isoformat(),
                    },
                }
            ],
        }

        mock_push = AsyncMock(return_value=conflict_response)
        mock_pull = AsyncMock(return_value={"attributes": [], "next_cursor": None})

        with (
            patch("handlers.sync.Cache", return_value=temp_cache),
            patch("handlers.sync.SETTINGS_FILE", settings_file),
            patch("handlers.sync.cloud_client") as mock_client,
        ):
            mock_client.push_attributes = mock_push
            mock_client.pull_attributes = mock_pull

            from handlers.sync import start_sync, SyncRequest

            await start_sync(SyncRequest(auth_token="test"))

        # After reconciliation, should not be unsynced
        unsynced = temp_cache.list_unsynced_attributes()
        ids = [a.image_id for a in unsynced]
        assert "reconciled" not in ids

    @pytest.mark.asyncio
    async def test_pull_loops_until_empty(self, temp_cache, tmp_path):
        """Should loop pull_attributes until empty page."""
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{}")

        page1_attrs = {
            "composition": 0.5,
            "subject_strength": 0.5,
            "visual_appeal": 0.5,
            "sharpness": 0.5,
            "exposure_balance": 0.5,
            "noise_level": 0.5,
        }

        mock_push = AsyncMock(return_value={"synced": 0, "conflicts": []})
        mock_pull = AsyncMock(
            side_effect=[
                {
                    "attributes": [
                        {
                            "image_id": "pull1",
                            "attributes": page1_attrs,
                            "scored_at": None,
                        }
                    ],
                    "next_cursor": {"since": "2026-03-24T10:00:00+00:00", "after_id": "uuid-1"},
                },
                {"attributes": [], "next_cursor": None},
            ]
        )

        with (
            patch("handlers.sync.Cache", return_value=temp_cache),
            patch("handlers.sync.SETTINGS_FILE", settings_file),
            patch("handlers.sync.cloud_client") as mock_client,
        ):
            mock_client.push_attributes = mock_push
            mock_client.pull_attributes = mock_pull

            from handlers.sync import start_sync, SyncRequest

            await start_sync(SyncRequest(auth_token="test"))

        # Should have called pull twice (page + empty)
        assert mock_pull.call_count == 2
        # Record should be in local cache
        local = temp_cache.get_attributes("pull1")
        assert local is not None
        assert local.composition == 0.5

    @pytest.mark.asyncio
    async def test_pull_marks_synced(self, temp_cache, tmp_path):
        """Pulled records should be marked as synced."""
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{}")

        pulled_attrs = {
            "composition": 0.5,
            "subject_strength": 0.5,
            "visual_appeal": 0.5,
            "sharpness": 0.5,
            "exposure_balance": 0.5,
            "noise_level": 0.5,
        }

        mock_push = AsyncMock(return_value={"synced": 0, "conflicts": []})
        mock_pull = AsyncMock(
            side_effect=[
                {
                    "attributes": [
                        {
                            "image_id": "pulled_img",
                            "attributes": pulled_attrs,
                            "scored_at": "2026-03-24T10:00:00+00:00",
                        }
                    ],
                    "next_cursor": None,
                },
            ]
        )

        with (
            patch("handlers.sync.Cache", return_value=temp_cache),
            patch("handlers.sync.SETTINGS_FILE", settings_file),
            patch("handlers.sync.cloud_client") as mock_client,
        ):
            mock_client.push_attributes = mock_push
            mock_client.pull_attributes = mock_pull

            from handlers.sync import start_sync, SyncRequest

            await start_sync(SyncRequest(auth_token="test"))

        unsynced = temp_cache.list_unsynced_attributes()
        ids = [a.image_id for a in unsynced]
        assert "pulled_img" not in ids

    @pytest.mark.asyncio
    async def test_persists_cursor(self, temp_cache, tmp_path):
        """Should persist pull cursor to settings.json."""
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{}")

        pulled_attrs = {
            "composition": 0.5,
            "subject_strength": 0.5,
            "visual_appeal": 0.5,
            "sharpness": 0.5,
            "exposure_balance": 0.5,
            "noise_level": 0.5,
        }

        mock_push = AsyncMock(return_value={"synced": 0, "conflicts": []})
        mock_pull = AsyncMock(
            side_effect=[
                {
                    "attributes": [
                        {
                            "image_id": "cursor_img",
                            "attributes": pulled_attrs,
                            "scored_at": None,
                        }
                    ],
                    "next_cursor": {
                        "since": "2026-03-24T12:00:00+00:00",
                        "after_id": "uuid-cursor",
                    },
                },
                {"attributes": [], "next_cursor": None},
            ]
        )

        with (
            patch("handlers.sync.Cache", return_value=temp_cache),
            patch("handlers.sync.SETTINGS_FILE", settings_file),
            patch("handlers.sync.cloud_client") as mock_client,
        ):
            mock_client.push_attributes = mock_push
            mock_client.pull_attributes = mock_pull

            from handlers.sync import start_sync, SyncRequest

            await start_sync(SyncRequest(auth_token="test"))

        saved = json.loads(settings_file.read_text())
        assert saved["sync_cursor_since"] == "2026-03-24T12:00:00+00:00"
        assert saved["sync_cursor_after_id"] == "uuid-cursor"

    @pytest.mark.asyncio
    async def test_handles_push_error_gracefully(self, temp_cache, tmp_path):
        """Should handle push errors and continue with pull."""
        now = datetime.now(timezone.utc)
        attrs = _make_attrs("err_img", scored_at=now)
        temp_cache.store_attributes(attrs)

        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{}")

        mock_push = AsyncMock(side_effect=Exception("Network error"))
        mock_pull = AsyncMock(return_value={"attributes": [], "next_cursor": None})

        with (
            patch("handlers.sync.Cache", return_value=temp_cache),
            patch("handlers.sync.SETTINGS_FILE", settings_file),
            patch("handlers.sync.cloud_client") as mock_client,
        ):
            mock_client.push_attributes = mock_push
            mock_client.pull_attributes = mock_pull

            from handlers.sync import start_sync, SyncRequest

            result = await start_sync(SyncRequest(auth_token="test"))

        assert result.status == "partial"
        assert len(result.errors) > 0
        assert "Push error" in result.errors[0]
