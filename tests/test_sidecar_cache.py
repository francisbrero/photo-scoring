"""Tests for sidecar cache-filtering behavior.

These tests verify that the desktop sidecar's cache interaction patterns
work correctly with the new composite-PK schema. They exercise the exact
filter values that inference.py and sync.py use, without requiring FastAPI.
"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from photo_score.storage.cache import Cache
from photo_score.storage.models import ImageMetadata, NormalizedAttributes

# Must match packages/desktop/sidecar/handlers/inference.py
CLOUD_MODEL_NAME = "anthropic/claude-3.5-sonnet"
CLOUD_MODEL_VERSION = "cloud-v1"

# Must match packages/desktop/sidecar/handlers/sync.py
SYNC_MODEL_NAME = "anthropic/claude-3.5-sonnet"
SYNC_MODEL_VERSION = "cloud-v1"


@pytest.fixture
def temp_cache() -> Cache:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_cache.db"
        yield Cache(db_path)


def _cloud_attrs(image_id: str, composition: float = 0.8, scored_at=None):
    return NormalizedAttributes(
        image_id=image_id,
        composition=composition,
        subject_strength=0.7,
        visual_appeal=0.6,
        sharpness=0.9,
        exposure_balance=0.85,
        noise_level=0.75,
        model_name=CLOUD_MODEL_NAME,
        model_version=CLOUD_MODEL_VERSION,
        scored_at=scored_at,
    )


def _local_attrs(image_id: str, composition: float = 0.5, scored_at=None):
    return NormalizedAttributes(
        image_id=image_id,
        composition=composition,
        subject_strength=0.5,
        visual_appeal=0.5,
        sharpness=0.5,
        exposure_balance=0.5,
        noise_level=0.5,
        model_name="local/qwen2-vl-2b-instruct",
        model_version="1.0",
        scored_at=scored_at,
    )


def _cli_cloud_attrs(image_id: str, composition: float = 0.7, scored_at=None):
    """CLI cloud uses the same model_name but different model_version."""
    return NormalizedAttributes(
        image_id=image_id,
        composition=composition,
        subject_strength=0.6,
        visual_appeal=0.5,
        sharpness=0.8,
        exposure_balance=0.8,
        noise_level=0.7,
        model_name="anthropic/claude-3.5-sonnet",
        model_version="20241022",
        scored_at=scored_at,
    )


class TestDesktopInferenceFiltering:
    """Tests that the desktop inference handler's cache patterns work.

    The sidecar inference.py filters all get_attributes calls by
    CLOUD_MODEL_NAME + CLOUD_MODEL_VERSION to only show desktop cloud scores.
    """

    def test_desktop_cloud_score_visible(self, temp_cache):
        """Desktop cloud scores should be visible with the sidecar's filter."""
        attrs = _cloud_attrs("img1")
        temp_cache.store_attributes(attrs)

        result = temp_cache.get_attributes(
            "img1", model_name=CLOUD_MODEL_NAME, model_version=CLOUD_MODEL_VERSION
        )
        assert result is not None
        assert result.composition == 0.8

    def test_local_score_invisible_to_desktop(self, temp_cache):
        """Local scores should NOT appear when desktop filters by cloud identity."""
        temp_cache.store_attributes(_local_attrs("img1"))

        result = temp_cache.get_attributes(
            "img1", model_name=CLOUD_MODEL_NAME, model_version=CLOUD_MODEL_VERSION
        )
        assert result is None

    def test_cli_cloud_score_invisible_to_desktop(self, temp_cache):
        """CLI cloud scores (different model_version) should NOT appear in desktop."""
        temp_cache.store_attributes(_cli_cloud_attrs("img1"))

        result = temp_cache.get_attributes(
            "img1", model_name=CLOUD_MODEL_NAME, model_version=CLOUD_MODEL_VERSION
        )
        assert result is None

    def test_all_three_backends_coexist(self, temp_cache):
        """Desktop cloud, CLI cloud, and local can all coexist for same image."""
        temp_cache.store_attributes(_cloud_attrs("img1", composition=0.9))
        temp_cache.store_attributes(_cli_cloud_attrs("img1", composition=0.7))
        temp_cache.store_attributes(_local_attrs("img1", composition=0.5))

        desktop = temp_cache.get_attributes(
            "img1", CLOUD_MODEL_NAME, CLOUD_MODEL_VERSION
        )
        cli_cloud = temp_cache.get_attributes(
            "img1", "anthropic/claude-3.5-sonnet", "20241022"
        )
        local = temp_cache.get_attributes("img1", "local/qwen2-vl-2b-instruct", "1.0")

        assert desktop.composition == 0.9
        assert cli_cloud.composition == 0.7
        assert local.composition == 0.5


class TestDesktopSyncFiltering:
    """Tests that the sync handler's cache patterns work.

    sync.py calls list_unsynced_attributes(model_name=SYNC_MODEL_NAME,
    model_version=SYNC_MODEL_VERSION) and mark_synced with full tuples.
    """

    def test_only_desktop_rows_in_push_batch(self, temp_cache):
        """list_unsynced with sync filter should only return desktop cloud rows."""
        now = datetime.now(timezone.utc)
        temp_cache.store_attributes(_cloud_attrs("img1", scored_at=now))
        temp_cache.store_attributes(_local_attrs("img2", scored_at=now))
        temp_cache.store_attributes(_cli_cloud_attrs("img3", scored_at=now))

        unsynced = temp_cache.list_unsynced_attributes(
            model_name=SYNC_MODEL_NAME, model_version=SYNC_MODEL_VERSION
        )

        ids = [a.image_id for a in unsynced]
        assert "img1" in ids
        assert "img2" not in ids  # local — excluded
        assert "img3" not in ids  # CLI cloud — excluded

    def test_mark_synced_tuple_only_marks_target(self, temp_cache):
        """mark_synced with tuple should only mark the specific desktop row."""
        now = datetime.now(timezone.utc)
        temp_cache.store_attributes(_cloud_attrs("img1", scored_at=now))
        temp_cache.store_attributes(_local_attrs("img1", scored_at=now))

        temp_cache.mark_synced([("img1", SYNC_MODEL_NAME, SYNC_MODEL_VERSION)])

        # Desktop row is synced
        desktop_unsynced = temp_cache.list_unsynced_attributes(
            model_name=SYNC_MODEL_NAME, model_version=SYNC_MODEL_VERSION
        )
        assert len(desktop_unsynced) == 0

        # Local row is still unsynced
        local_unsynced = temp_cache.list_unsynced_attributes(
            model_name="local/qwen2-vl-2b-instruct", model_version="1.0"
        )
        assert len(local_unsynced) == 1

    def test_metadata_filtered_by_model_for_sync(self, temp_cache):
        """list_all_metadata_for with model filter should match sync behavior."""
        cloud_meta = ImageMetadata(description="Cloud desc")
        local_meta = ImageMetadata(description="Local desc")

        temp_cache.store_metadata("img1", cloud_meta, model_name=SYNC_MODEL_NAME)
        temp_cache.store_metadata(
            "img1", local_meta, model_name="local/qwen2-vl-2b-instruct"
        )

        result = temp_cache.list_all_metadata_for(["img1"], model_name=SYNC_MODEL_NAME)
        assert len(result) == 1
        assert result["img1"].description == "Cloud desc"


class TestMigrationPreservesDesktopVisibility:
    """Tests that migrated legacy rows are visible to the desktop sidecar."""

    def test_migrated_rows_visible_with_desktop_filter(self):
        """Legacy single-PK rows should be visible after migration with desktop filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "legacy.db"

            import sqlite3

            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    CREATE TABLE normalized_attributes (
                        image_id TEXT PRIMARY KEY,
                        composition REAL NOT NULL,
                        subject_strength REAL NOT NULL,
                        visual_appeal REAL NOT NULL,
                        sharpness REAL NOT NULL,
                        exposure_balance REAL NOT NULL,
                        noise_level REAL NOT NULL,
                        model_name TEXT,
                        model_version TEXT
                    )
                """)
                # Row with NULL model fields (earliest schema)
                conn.execute(
                    "INSERT INTO normalized_attributes VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL)",
                    ("null_model", 0.8, 0.7, 0.6, 0.9, 0.85, 0.75),
                )
                # Row with 'unknown' model fields (intermediate state)
                conn.execute(
                    "INSERT INTO normalized_attributes VALUES (?, ?, ?, ?, ?, ?, ?, 'unknown', 'unknown')",
                    ("unknown_model", 0.5, 0.5, 0.5, 0.5, 0.5, 0.5),
                )
                # Row with actual cloud model name (already correct)
                conn.execute(
                    "INSERT INTO normalized_attributes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        "cloud_model",
                        0.6,
                        0.6,
                        0.6,
                        0.6,
                        0.6,
                        0.6,
                        "anthropic/claude-3.5-sonnet",
                        "20241022",
                    ),
                )
                conn.execute("""
                    CREATE TABLE image_metadata (
                        image_id TEXT PRIMARY KEY,
                        date_taken TEXT,
                        latitude REAL,
                        longitude REAL,
                        description TEXT,
                        location_name TEXT,
                        location_country TEXT
                    )
                """)
                conn.execute(
                    "INSERT INTO image_metadata (image_id, description) VALUES (?, ?)",
                    ("null_model", "Legacy photo"),
                )
                conn.commit()

            # Migration runs on Cache init
            cache = Cache(db_path)

            # NULL-model rows should now be visible with desktop filter
            null_row = cache.get_attributes(
                "null_model", CLOUD_MODEL_NAME, CLOUD_MODEL_VERSION
            )
            assert null_row is not None, (
                "NULL model_name row should be migrated to cloud identity"
            )
            assert null_row.composition == 0.8

            # 'unknown' rows should also be migrated to cloud identity
            unknown_row = cache.get_attributes(
                "unknown_model", CLOUD_MODEL_NAME, CLOUD_MODEL_VERSION
            )
            assert unknown_row is not None, (
                "'unknown' model row should be migrated to cloud identity"
            )

            # Rows with explicit model_name preserve their identity (not relabeled)
            cloud_row = cache.get_attributes(
                "cloud_model", "anthropic/claude-3.5-sonnet", "20241022"
            )
            assert cloud_row is not None, (
                "Explicit model identity must be preserved during migration"
            )
            assert cloud_row.model_version == "20241022"

            # Such rows are NOT visible under the desktop cloud-v1 filter
            desktop_cloud = cache.get_attributes(
                "cloud_model", CLOUD_MODEL_NAME, CLOUD_MODEL_VERSION
            )
            assert desktop_cloud is None, (
                "Explicit model_version must not be relabeled to cloud-v1"
            )

            # Legacy metadata should also be visible
            meta = cache.get_metadata("null_model", model_name=CLOUD_MODEL_NAME)
            assert meta is not None
            assert meta.description == "Legacy photo"

    def test_migrated_rows_appear_in_sync_push(self):
        """Migrated rows should appear in sync push (unsynced with correct identity)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "legacy_sync.db"

            import sqlite3

            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    CREATE TABLE normalized_attributes (
                        image_id TEXT PRIMARY KEY,
                        composition REAL NOT NULL,
                        subject_strength REAL NOT NULL,
                        visual_appeal REAL NOT NULL,
                        sharpness REAL NOT NULL,
                        exposure_balance REAL NOT NULL,
                        noise_level REAL NOT NULL,
                        model_name TEXT,
                        model_version TEXT
                    )
                """)
                conn.execute(
                    "INSERT INTO normalized_attributes VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL)",
                    ("sync_me", 0.8, 0.7, 0.6, 0.9, 0.85, 0.75),
                )
                conn.commit()

            cache = Cache(db_path)

            unsynced = cache.list_unsynced_attributes(
                model_name=SYNC_MODEL_NAME, model_version=SYNC_MODEL_VERSION
            )
            ids = [a.image_id for a in unsynced]
            assert "sync_me" in ids
