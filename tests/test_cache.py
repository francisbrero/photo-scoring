"""Tests for SQLite cache layer."""

import sqlite3
import tempfile
from datetime import datetime, timezone, timedelta
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


def _make_attrs(
    image_id: str = "abc123",
    composition: float = 0.8,
    model_name: str = "test/model",
    model_version: str = "1.0",
    scored_at: datetime | None = None,
    **kwargs,
) -> NormalizedAttributes:
    """Helper to create NormalizedAttributes with sensible defaults."""
    return NormalizedAttributes(
        image_id=image_id,
        composition=composition,
        subject_strength=kwargs.get("subject_strength", 0.7),
        visual_appeal=kwargs.get("visual_appeal", 0.6),
        sharpness=kwargs.get("sharpness", 0.9),
        exposure_balance=kwargs.get("exposure_balance", 0.85),
        noise_level=kwargs.get("noise_level", 0.75),
        model_name=model_name,
        model_version=model_version,
        scored_at=scored_at,
    )


class TestCache:
    """Tests for Cache class."""

    def test_store_and_retrieve_attributes(self, temp_cache: Cache):
        """Should store and retrieve attributes correctly."""
        attrs = _make_attrs()
        temp_cache.store_attributes(attrs)
        retrieved = temp_cache.get_attributes("abc123", "test/model", "1.0")

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
        attrs = _make_attrs(image_id="exists123", composition=0.5)

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
        """Storing attributes again with same PK should update existing entry."""
        attrs1 = _make_attrs(image_id="update_test", composition=0.5)
        attrs2 = _make_attrs(image_id="update_test", composition=0.9)

        temp_cache.store_attributes(attrs1)
        temp_cache.store_attributes(attrs2)

        retrieved = temp_cache.get_attributes("update_test", "test/model", "1.0")
        assert retrieved.composition == 0.9


class TestCompositeKeyAttributes:
    """Tests for multi-model attribute coexistence."""

    def test_cloud_and_local_attrs_coexist(self, temp_cache: Cache):
        """Cloud and local attrs for same image should both exist."""
        cloud = _make_attrs(
            image_id="img1",
            model_name="anthropic/claude-3.5-sonnet",
            model_version="20241022",
            composition=0.8,
        )
        local = _make_attrs(
            image_id="img1",
            model_name="local/qwen2-vl-2b-instruct",
            model_version="1.0",
            composition=0.6,
        )

        temp_cache.store_attributes(cloud)
        temp_cache.store_attributes(local)

        got_cloud = temp_cache.get_attributes(
            "img1", "anthropic/claude-3.5-sonnet", "20241022"
        )
        got_local = temp_cache.get_attributes(
            "img1", "local/qwen2-vl-2b-instruct", "1.0"
        )

        assert got_cloud is not None
        assert got_local is not None
        assert got_cloud.composition == 0.8
        assert got_local.composition == 0.6

    def test_get_attributes_no_filter_returns_latest(self, temp_cache: Cache):
        """get_attributes with no model filter returns most recent by scored_at."""
        old_time = datetime.now(timezone.utc) - timedelta(hours=1)
        new_time = datetime.now(timezone.utc)

        old = _make_attrs(
            image_id="img1",
            model_name="model/old",
            model_version="1.0",
            scored_at=old_time,
            composition=0.3,
        )
        new = _make_attrs(
            image_id="img1",
            model_name="model/new",
            model_version="2.0",
            scored_at=new_time,
            composition=0.9,
        )

        temp_cache.store_attributes(old)
        temp_cache.store_attributes(new)

        latest = temp_cache.get_attributes("img1")
        assert latest is not None
        assert latest.composition == 0.9

    def test_has_attributes_with_model_filter(self, temp_cache: Cache):
        """has_attributes should filter by model when provided."""
        attrs = _make_attrs(
            image_id="img1",
            model_name="cloud/model",
            model_version="v1",
        )
        temp_cache.store_attributes(attrs)

        assert temp_cache.has_attributes("img1", "cloud/model", "v1")
        assert not temp_cache.has_attributes("img1", "local/model", "v1")
        assert temp_cache.has_attributes("img1")  # no filter

    def test_has_attributes_model_name_only(self, temp_cache: Cache):
        """has_attributes with model_name only should work."""
        attrs = _make_attrs(
            image_id="img1",
            model_name="cloud/model",
            model_version="v1",
        )
        temp_cache.store_attributes(attrs)

        assert temp_cache.has_attributes("img1", model_name="cloud/model")
        assert not temp_cache.has_attributes("img1", model_name="local/model")


class TestCompositeKeyMetadata:
    """Tests for multi-model metadata coexistence."""

    def test_cloud_and_local_metadata_coexist(self, temp_cache: Cache):
        """Cloud and local metadata for same image should both exist."""
        cloud_meta = ImageMetadata(
            description="Cloud description", location_name="Paris"
        )
        local_meta = ImageMetadata(
            description="Local description", location_name="Lyon"
        )

        temp_cache.store_metadata("img1", cloud_meta, model_name="cloud/model")
        temp_cache.store_metadata("img1", local_meta, model_name="local/model")

        got_cloud = temp_cache.get_metadata("img1", model_name="cloud/model")
        got_local = temp_cache.get_metadata("img1", model_name="local/model")

        assert got_cloud is not None
        assert got_local is not None
        assert got_cloud.description == "Cloud description"
        assert got_local.description == "Local description"

    def test_get_metadata_no_filter_returns_one(self, temp_cache: Cache):
        """get_metadata with no model filter returns a result."""
        meta = ImageMetadata(description="test")
        temp_cache.store_metadata("img1", meta, model_name="some/model")

        result = temp_cache.get_metadata("img1")
        assert result is not None
        assert result.description == "test"

    def test_has_metadata_with_model_filter(self, temp_cache: Cache):
        """has_metadata should filter by model when provided."""
        meta = ImageMetadata(description="test")
        temp_cache.store_metadata("img1", meta, model_name="cloud/model")

        assert temp_cache.has_metadata("img1", model_name="cloud/model")
        assert not temp_cache.has_metadata("img1", model_name="local/model")
        assert temp_cache.has_metadata("img1")  # no filter

    def test_list_all_metadata_for_with_model_filter(self, temp_cache: Cache):
        """list_all_metadata_for should filter by model_name."""
        cloud_meta = ImageMetadata(description="Cloud")
        local_meta = ImageMetadata(description="Local")

        temp_cache.store_metadata("img1", cloud_meta, model_name="cloud/model")
        temp_cache.store_metadata("img1", local_meta, model_name="local/model")
        temp_cache.store_metadata("img2", cloud_meta, model_name="cloud/model")

        result = temp_cache.list_all_metadata_for(
            ["img1", "img2"], model_name="cloud/model"
        )
        assert len(result) == 2
        assert result["img1"].description == "Cloud"
        assert result["img2"].description == "Cloud"

    def test_list_all_metadata_for_without_filter(self, temp_cache: Cache):
        """list_all_metadata_for without filter returns one per image."""
        meta1 = ImageMetadata(description="Photo 1", location_name="Paris")
        meta2 = ImageMetadata(description="Photo 2", location_country="Japan")

        temp_cache.store_metadata("img1", meta1)
        temp_cache.store_metadata("img2", meta2)

        result = temp_cache.list_all_metadata_for(["img1", "img2"])
        assert len(result) == 2
        assert result["img1"].description == "Photo 1"
        assert result["img2"].description == "Photo 2"


class TestSyncFeatures:
    """Tests for sync-related cache features."""

    def test_scored_at_roundtrips(self, temp_cache: Cache):
        """scored_at should round-trip through store/get."""
        now = datetime.now(timezone.utc)
        attrs = _make_attrs(image_id="scored1", scored_at=now)
        temp_cache.store_attributes(attrs)
        retrieved = temp_cache.get_attributes("scored1", "test/model", "1.0")
        assert retrieved is not None
        assert retrieved.scored_at is not None
        assert retrieved.scored_at.isoformat() == now.isoformat()

    def test_scored_at_none_roundtrips(self, temp_cache: Cache):
        """scored_at=None should round-trip as None."""
        attrs = _make_attrs(image_id="scored_none", scored_at=None)
        temp_cache.store_attributes(attrs)
        retrieved = temp_cache.get_attributes("scored_none", "test/model", "1.0")
        assert retrieved is not None
        assert retrieved.scored_at is None

    def test_synced_at_none_on_fresh_store(self, temp_cache: Cache):
        """synced_at should be None after initial store."""
        attrs = _make_attrs(image_id="fresh1")
        temp_cache.store_attributes(attrs)

        with sqlite3.connect(temp_cache.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT synced_at FROM normalized_attributes WHERE image_id = ?",
                ("fresh1",),
            ).fetchone()
            assert row["synced_at"] is None

    def test_mark_synced_with_tuples(self, temp_cache: Cache):
        """mark_synced with (image_id, model_name, model_version) tuples should work."""
        attrs = _make_attrs(image_id="sync1")
        temp_cache.store_attributes(attrs)
        temp_cache.mark_synced([("sync1", "test/model", "1.0")])

        with sqlite3.connect(temp_cache.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT synced_at FROM normalized_attributes WHERE image_id = ?",
                ("sync1",),
            ).fetchone()
            assert row["synced_at"] is not None

    def test_mark_synced_with_strings_backward_compat(self, temp_cache: Cache):
        """mark_synced with plain image_id strings should still work."""
        attrs = _make_attrs(image_id="sync_str")
        temp_cache.store_attributes(attrs)
        temp_cache.mark_synced(["sync_str"])

        with sqlite3.connect(temp_cache.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT synced_at FROM normalized_attributes WHERE image_id = ?",
                ("sync_str",),
            ).fetchone()
            assert row["synced_at"] is not None

    def test_mark_synced_targets_specific_row(self, temp_cache: Cache):
        """mark_synced with tuples should only mark the exact row."""
        cloud = _make_attrs(
            image_id="img1",
            model_name="cloud/model",
            model_version="v1",
        )
        local = _make_attrs(
            image_id="img1",
            model_name="local/model",
            model_version="v1",
        )
        temp_cache.store_attributes(cloud)
        temp_cache.store_attributes(local)

        # Mark only cloud row as synced
        temp_cache.mark_synced([("img1", "cloud/model", "v1")])

        with sqlite3.connect(temp_cache.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cloud_row = conn.execute(
                "SELECT synced_at FROM normalized_attributes WHERE image_id = ? AND model_name = ?",
                ("img1", "cloud/model"),
            ).fetchone()
            local_row = conn.execute(
                "SELECT synced_at FROM normalized_attributes WHERE image_id = ? AND model_name = ?",
                ("img1", "local/model"),
            ).fetchone()

            assert cloud_row["synced_at"] is not None
            assert local_row["synced_at"] is None

    def test_list_unsynced_returns_new_rows(self, temp_cache: Cache):
        """list_unsynced_attributes should return rows with synced_at IS NULL."""
        attrs = _make_attrs(image_id="unsynced1")
        temp_cache.store_attributes(attrs)

        unsynced = temp_cache.list_unsynced_attributes()
        ids = [a.image_id for a in unsynced]
        assert "unsynced1" in ids

    def test_list_unsynced_with_model_filter(self, temp_cache: Cache):
        """list_unsynced_attributes should filter by model when provided."""
        cloud = _make_attrs(
            image_id="img1", model_name="cloud/model", model_version="v1"
        )
        local = _make_attrs(
            image_id="img1", model_name="local/model", model_version="v1"
        )
        temp_cache.store_attributes(cloud)
        temp_cache.store_attributes(local)

        cloud_unsynced = temp_cache.list_unsynced_attributes(
            model_name="cloud/model", model_version="v1"
        )
        local_unsynced = temp_cache.list_unsynced_attributes(
            model_name="local/model", model_version="v1"
        )
        all_unsynced = temp_cache.list_unsynced_attributes()

        assert len(cloud_unsynced) == 1
        assert cloud_unsynced[0].model_name == "cloud/model"
        assert len(local_unsynced) == 1
        assert local_unsynced[0].model_name == "local/model"
        assert len(all_unsynced) == 2

    def test_mark_synced_makes_rows_no_longer_unsynced(self, temp_cache: Cache):
        """After mark_synced, rows should not appear in list_unsynced."""
        now = datetime.now(timezone.utc)
        attrs = _make_attrs(image_id="will_sync", scored_at=now)
        temp_cache.store_attributes(attrs)
        temp_cache.mark_synced([("will_sync", "test/model", "1.0")])

        unsynced = temp_cache.list_unsynced_attributes()
        ids = [a.image_id for a in unsynced]
        assert "will_sync" not in ids

    def test_list_unsynced_returns_changed_rows(self, temp_cache: Cache):
        """Rows with scored_at > synced_at should appear as unsynced."""
        old_time = datetime.now(timezone.utc) - timedelta(hours=1)
        attrs = _make_attrs(image_id="changed1", scored_at=old_time)
        temp_cache.store_attributes(attrs)
        temp_cache.mark_synced([("changed1", "test/model", "1.0")])

        # Now re-score with newer scored_at
        new_time = datetime.now(timezone.utc)
        attrs.scored_at = new_time
        temp_cache.store_attributes(attrs)

        unsynced = temp_cache.list_unsynced_attributes()
        ids = [a.image_id for a in unsynced]
        assert "changed1" in ids

    def test_store_preserves_synced_at(self, temp_cache: Cache):
        """store_attributes should not null out synced_at on update."""
        attrs = _make_attrs(image_id="preserve1")
        temp_cache.store_attributes(attrs)
        temp_cache.mark_synced([("preserve1", "test/model", "1.0")])

        # Update attributes (new store)
        attrs.composition = 0.9
        temp_cache.store_attributes(attrs)

        # synced_at should still be set (not nulled by store)
        with sqlite3.connect(temp_cache.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT synced_at FROM normalized_attributes WHERE image_id = ? AND model_name = ? AND model_version = ?",
                ("preserve1", "test/model", "1.0"),
            ).fetchone()
            assert row["synced_at"] is not None

    def test_list_all_metadata_for_empty(self, temp_cache: Cache):
        """list_all_metadata_for with empty list should return empty dict."""
        result = temp_cache.list_all_metadata_for([])
        assert result == {}

    def test_mark_synced_empty_list(self, temp_cache: Cache):
        """mark_synced with empty list should be a no-op."""
        temp_cache.mark_synced([])  # Should not raise


class TestMigration:
    """Tests for schema migration."""

    def test_migration_adds_columns_to_existing_db(self):
        """Migration should add scored_at and synced_at to existing DBs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "migrate_test.db"
            # Create DB with old schema (no scored_at/synced_at, single PK)
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
                # Insert test data with NULL model_name
                conn.execute(
                    """
                    INSERT INTO normalized_attributes
                    (image_id, composition, subject_strength, visual_appeal,
                     sharpness, exposure_balance, noise_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    ("old_img", 0.5, 0.5, 0.5, 0.5, 0.5, 0.5),
                )
                conn.execute(
                    """
                    INSERT INTO image_metadata (image_id, description)
                    VALUES (?, ?)
                """,
                    ("old_img", "Old description"),
                )
                conn.commit()

            # Opening Cache should trigger migration
            cache = Cache(db_path)

            # Verify composite PK for normalized_attributes
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("PRAGMA table_info(normalized_attributes)")
                columns = {row[1]: row for row in cursor.fetchall()}
                assert "scored_at" in columns
                assert "synced_at" in columns
                # Check that model_name is NOT NULL (composite PK)
                pk_cols = [name for name, row in columns.items() if row[5] > 0]
                assert set(pk_cols) == {"image_id", "model_name", "model_version"}

            # Verify composite PK for image_metadata
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("PRAGMA table_info(image_metadata)")
                columns = {row[1]: row for row in cursor.fetchall()}
                assert "model_name" in columns
                pk_cols = [name for name, row in columns.items() if row[5] > 0]
                assert set(pk_cols) == {"image_id", "model_name"}

            # Verify old data was migrated to canonical cloud identity
            attrs = cache.get_attributes("old_img")
            assert attrs is not None
            assert attrs.model_name == "anthropic/claude-3.5-sonnet"
            assert attrs.model_version == "cloud-v1"

            meta = cache.get_metadata("old_img")
            assert meta is not None
            assert meta.description == "Old description"

    def test_migration_preserves_explicit_model_identity(self):
        """Rows with explicit model_name should NOT be overwritten to cloud identity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "explicit_model.db"

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
                # Row with explicit non-default model identity
                conn.execute(
                    """INSERT INTO normalized_attributes VALUES
                       (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        "gemini_img",
                        0.7,
                        0.7,
                        0.7,
                        0.7,
                        0.7,
                        0.7,
                        "google/gemini-1.5-pro",
                        "exp-42",
                    ),
                )
                # Row with NULL model (genuinely legacy)
                conn.execute(
                    """INSERT INTO normalized_attributes
                       (image_id, composition, subject_strength, visual_appeal,
                        sharpness, exposure_balance, noise_level)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    ("legacy_img", 0.5, 0.5, 0.5, 0.5, 0.5, 0.5),
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
                conn.commit()

            cache = Cache(db_path)

            # Explicit model identity must be preserved
            gemini = cache.get_attributes(
                "gemini_img", "google/gemini-1.5-pro", "exp-42"
            )
            assert gemini is not None, "Explicit model identity must survive migration"
            assert gemini.model_name == "google/gemini-1.5-pro"
            assert gemini.model_version == "exp-42"

            # It must NOT appear under the cloud identity
            cloud_gemini = cache.get_attributes(
                "gemini_img", "anthropic/claude-3.5-sonnet", "cloud-v1"
            )
            assert cloud_gemini is None, "Explicit model must not be relabeled as cloud"

            # NULL model row should be normalized to cloud identity
            legacy = cache.get_attributes(
                "legacy_img", "anthropic/claude-3.5-sonnet", "cloud-v1"
            )
            assert legacy is not None, "NULL model row should become cloud identity"

    def test_migration_is_idempotent(self):
        """Running migration on already-migrated DB should be safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "idempotent.db"
            # Create fresh cache (new schema)
            cache1 = Cache(db_path)
            attrs = _make_attrs(image_id="test1")
            cache1.store_attributes(attrs)

            # Open again — migration should be a no-op
            cache2 = Cache(db_path)
            retrieved = cache2.get_attributes("test1", "test/model", "1.0")
            assert retrieved is not None
            assert retrieved.composition == 0.8


class TestDefaultModelValues:
    """Tests for NormalizedAttributes default model values."""

    def test_default_model_name_is_unknown(self):
        """NormalizedAttributes should default model_name to 'unknown'."""
        attrs = NormalizedAttributes(
            image_id="test",
            composition=0.5,
            subject_strength=0.5,
            visual_appeal=0.5,
            sharpness=0.5,
            exposure_balance=0.5,
            noise_level=0.5,
        )
        assert attrs.model_name == "unknown"
        assert attrs.model_version == "unknown"

    def test_model_name_can_be_set(self):
        """NormalizedAttributes should accept explicit model_name."""
        attrs = NormalizedAttributes(
            image_id="test",
            composition=0.5,
            subject_strength=0.5,
            visual_appeal=0.5,
            sharpness=0.5,
            exposure_balance=0.5,
            noise_level=0.5,
            model_name="anthropic/claude-3.5-sonnet",
            model_version="20241022",
        )
        assert attrs.model_name == "anthropic/claude-3.5-sonnet"
        assert attrs.model_version == "20241022"
