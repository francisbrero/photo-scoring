"""Tests for SQLite cache layer."""

import tempfile
from pathlib import Path

import pytest

from photo_score.storage.cache import Cache
from photo_score.storage.models import NormalizedAttributes


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
