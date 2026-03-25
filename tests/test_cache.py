"""Tests for SQLite cache layer."""

import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from photo_score.storage.cache import Cache
from photo_score.storage.models import ImageMetadata, NormalizedAttributes


@pytest.fixture
def temp_cache() -> Cache:
    """Create a cache with a temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_cache.db"
        yield Cache(db_path)


class TestCache:
    """Tests for Cache class."""

    def test_store_and_retrieve_attributes(self, temp_cache: Cache):
        """Should store and retrieve attributes correctly."""
        attrs = NormalizedAttributes(
            image_id="abc123",
            composition=0.8,
            subject_strength=0.7,
            visual_appeal=0.6,
            sharpness=0.9,
            exposure_balance=0.85,
            noise_level=0.75,
            model_name="test/model",
            model_version="1.0",
        )

        temp_cache.store_attributes(attrs)
        retrieved = temp_cache.get_attributes("abc123")

        assert retrieved is not None
        assert retrieved.image_id == attrs.image_id
        assert retrieved.composition == attrs.composition
        assert retrieved.sharpness == attrs.sharpness

    def test_get_missing_attributes(self, temp_cache: Cache):
        """Should return None for missing attributes."""
        result = temp_cache.get_attributes("nonexistent")
        assert result is None

    def test_has_attributes(self, temp_cache: Cache):
        """Should correctly check for attribute existence."""
        attrs = NormalizedAttributes(
            image_id="exists123",
            composition=0.5,
            subject_strength=0.5,
            visual_appeal=0.5,
            sharpness=0.5,
            exposure_balance=0.5,
            noise_level=0.5,
        )

        assert not temp_cache.has_attributes("exists123")
        temp_cache.store_attributes(attrs)
        assert temp_cache.has_attributes("exists123")

    def test_store_and_retrieve_inference(self, temp_cache: Cache):
        """Should store and retrieve inference results."""
        raw_response = {
            "composition": 0.8,
            "subject_strength": 0.7,
            "visual_appeal": 0.6,
        }

        temp_cache.store_inference(
            image_id="img456",
            model_name="test/model",
            model_version="2.0",
            raw_response=raw_response,
        )

        retrieved = temp_cache.get_inference("img456", "test/model", "2.0")

        assert retrieved is not None
        assert retrieved.image_id == "img456"
        assert retrieved.raw_response == raw_response

    def test_get_missing_inference(self, temp_cache: Cache):
        """Should return None for missing inference."""
        result = temp_cache.get_inference("missing", "model", "1.0")
        assert result is None

    def test_inference_keyed_by_version(self, temp_cache: Cache):
        """Different model versions should be stored separately."""
        response_v1 = {"composition": 0.5}
        response_v2 = {"composition": 0.8}

        temp_cache.store_inference("img", "model", "1.0", response_v1)
        temp_cache.store_inference("img", "model", "2.0", response_v2)

        v1 = temp_cache.get_inference("img", "model", "1.0")
        v2 = temp_cache.get_inference("img", "model", "2.0")

        assert v1.raw_response == response_v1
        assert v2.raw_response == response_v2

    def test_update_existing_attributes(self, temp_cache: Cache):
        """Storing attributes again should update existing entry."""
        attrs1 = NormalizedAttributes(
            image_id="update_test",
            composition=0.5,
            subject_strength=0.5,
            visual_appeal=0.5,
            sharpness=0.5,
            exposure_balance=0.5,
            noise_level=0.5,
        )
        attrs2 = NormalizedAttributes(
            image_id="update_test",
            composition=0.9,  # Changed
            subject_strength=0.5,
            visual_appeal=0.5,
            sharpness=0.5,
            exposure_balance=0.5,
            noise_level=0.5,
        )

        temp_cache.store_attributes(attrs1)
        temp_cache.store_attributes(attrs2)

        retrieved = temp_cache.get_attributes("update_test")
        assert retrieved.composition == 0.9


class TestSyncFeatures:
    """Tests for sync-related cache features."""

    def test_scored_at_roundtrips(self, temp_cache: Cache):
        """scored_at should round-trip through store/get."""
        now = datetime.now(timezone.utc)
        attrs = NormalizedAttributes(
            image_id="scored1",
            composition=0.5,
            subject_strength=0.5,
            visual_appeal=0.5,
            sharpness=0.5,
            exposure_balance=0.5,
            noise_level=0.5,
            scored_at=now,
        )
        temp_cache.store_attributes(attrs)
        retrieved = temp_cache.get_attributes("scored1")
        assert retrieved is not None
        assert retrieved.scored_at is not None
        assert retrieved.scored_at.isoformat() == now.isoformat()

    def test_scored_at_none_roundtrips(self, temp_cache: Cache):
        """scored_at=None should round-trip as None."""
        attrs = NormalizedAttributes(
            image_id="scored_none",
            composition=0.5,
            subject_strength=0.5,
            visual_appeal=0.5,
            sharpness=0.5,
            exposure_balance=0.5,
            noise_level=0.5,
            scored_at=None,
        )
        temp_cache.store_attributes(attrs)
        retrieved = temp_cache.get_attributes("scored_none")
        assert retrieved is not None
        assert retrieved.scored_at is None

    def test_synced_at_none_on_fresh_store(self, temp_cache: Cache):
        """synced_at should be None after initial store."""
        attrs = NormalizedAttributes(
            image_id="fresh1",
            composition=0.5,
            subject_strength=0.5,
            visual_appeal=0.5,
            sharpness=0.5,
            exposure_balance=0.5,
            noise_level=0.5,
        )
        temp_cache.store_attributes(attrs)

        # Check directly in DB that synced_at is NULL
        with sqlite3.connect(temp_cache.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT synced_at FROM normalized_attributes WHERE image_id = ?",
                ("fresh1",),
            ).fetchone()
            assert row["synced_at"] is None

    def test_mark_synced_sets_synced_at(self, temp_cache: Cache):
        """mark_synced should set synced_at for given ids."""
        attrs = NormalizedAttributes(
            image_id="sync1",
            composition=0.5,
            subject_strength=0.5,
            visual_appeal=0.5,
            sharpness=0.5,
            exposure_balance=0.5,
            noise_level=0.5,
        )
        temp_cache.store_attributes(attrs)
        temp_cache.mark_synced(["sync1"])

        with sqlite3.connect(temp_cache.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT synced_at FROM normalized_attributes WHERE image_id = ?",
                ("sync1",),
            ).fetchone()
            assert row["synced_at"] is not None

    def test_list_unsynced_returns_new_rows(self, temp_cache: Cache):
        """list_unsynced_attributes should return rows with synced_at IS NULL."""
        attrs = NormalizedAttributes(
            image_id="unsynced1",
            composition=0.5,
            subject_strength=0.5,
            visual_appeal=0.5,
            sharpness=0.5,
            exposure_balance=0.5,
            noise_level=0.5,
        )
        temp_cache.store_attributes(attrs)

        unsynced = temp_cache.list_unsynced_attributes()
        ids = [a.image_id for a in unsynced]
        assert "unsynced1" in ids

    def test_mark_synced_makes_rows_no_longer_unsynced(self, temp_cache: Cache):
        """After mark_synced, rows should not appear in list_unsynced."""
        now = datetime.now(timezone.utc)
        attrs = NormalizedAttributes(
            image_id="will_sync",
            composition=0.5,
            subject_strength=0.5,
            visual_appeal=0.5,
            sharpness=0.5,
            exposure_balance=0.5,
            noise_level=0.5,
            scored_at=now,
        )
        temp_cache.store_attributes(attrs)
        temp_cache.mark_synced(["will_sync"])

        unsynced = temp_cache.list_unsynced_attributes()
        ids = [a.image_id for a in unsynced]
        assert "will_sync" not in ids

    def test_list_unsynced_returns_changed_rows(self, temp_cache: Cache):
        """Rows with scored_at > synced_at should appear as unsynced."""
        from datetime import timedelta

        old_time = datetime.now(timezone.utc) - timedelta(hours=1)
        attrs = NormalizedAttributes(
            image_id="changed1",
            composition=0.5,
            subject_strength=0.5,
            visual_appeal=0.5,
            sharpness=0.5,
            exposure_balance=0.5,
            noise_level=0.5,
            scored_at=old_time,
        )
        temp_cache.store_attributes(attrs)
        temp_cache.mark_synced(["changed1"])

        # Now re-score with newer scored_at
        new_time = datetime.now(timezone.utc)
        attrs.scored_at = new_time
        temp_cache.store_attributes(attrs)

        unsynced = temp_cache.list_unsynced_attributes()
        ids = [a.image_id for a in unsynced]
        assert "changed1" in ids

    def test_store_preserves_synced_at(self, temp_cache: Cache):
        """store_attributes should not null out synced_at on update."""
        attrs = NormalizedAttributes(
            image_id="preserve1",
            composition=0.5,
            subject_strength=0.5,
            visual_appeal=0.5,
            sharpness=0.5,
            exposure_balance=0.5,
            noise_level=0.5,
        )
        temp_cache.store_attributes(attrs)
        temp_cache.mark_synced(["preserve1"])

        # Update attributes (new store)
        attrs.composition = 0.9
        temp_cache.store_attributes(attrs)

        # synced_at should still be set (not nulled by store)
        with sqlite3.connect(temp_cache.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT synced_at FROM normalized_attributes WHERE image_id = ?",
                ("preserve1",),
            ).fetchone()
            assert row["synced_at"] is not None

    def test_list_all_metadata_for(self, temp_cache: Cache):
        """list_all_metadata_for should return correct dict for given ids."""
        meta1 = ImageMetadata(description="Photo 1", location_name="Paris")
        meta2 = ImageMetadata(description="Photo 2", location_country="Japan")

        temp_cache.store_metadata("img1", meta1)
        temp_cache.store_metadata("img2", meta2)
        temp_cache.store_metadata("img3", ImageMetadata(description="Not requested"))

        result = temp_cache.list_all_metadata_for(["img1", "img2"])
        assert len(result) == 2
        assert result["img1"].description == "Photo 1"
        assert result["img1"].location_name == "Paris"
        assert result["img2"].description == "Photo 2"
        assert result["img2"].location_country == "Japan"

    def test_list_all_metadata_for_empty(self, temp_cache: Cache):
        """list_all_metadata_for with empty list should return empty dict."""
        result = temp_cache.list_all_metadata_for([])
        assert result == {}

    def test_mark_synced_empty_list(self, temp_cache: Cache):
        """mark_synced with empty list should be a no-op."""
        temp_cache.mark_synced([])  # Should not raise

    def test_migration_adds_columns_to_existing_db(self):
        """Migration should add scored_at and synced_at to existing DBs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "migrate_test.db"
            # Create DB with old schema (no scored_at/synced_at)
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
                conn.commit()

            # Opening Cache should trigger migration
            Cache(db_path)

            # Verify columns exist
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("PRAGMA table_info(normalized_attributes)")
                columns = {row[1] for row in cursor.fetchall()}
                assert "scored_at" in columns
                assert "synced_at" in columns
