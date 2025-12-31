"""Tests for scoring reducer."""

import pytest

from photo_score.config.schema import ScoringConfig
from photo_score.scoring.reducer import ScoringReducer
from photo_score.storage.models import NormalizedAttributes


@pytest.fixture
def default_config() -> ScoringConfig:
    """Default scoring configuration."""
    return ScoringConfig()


@pytest.fixture
def reducer(default_config: ScoringConfig) -> ScoringReducer:
    """Scoring reducer with default config."""
    return ScoringReducer(default_config)


@pytest.fixture
def perfect_attributes() -> NormalizedAttributes:
    """Attributes with all values at 1.0."""
    return NormalizedAttributes(
        image_id="test123",
        composition=1.0,
        subject_strength=1.0,
        visual_appeal=1.0,
        sharpness=1.0,
        exposure_balance=1.0,
        noise_level=1.0,
    )


@pytest.fixture
def poor_attributes() -> NormalizedAttributes:
    """Attributes with all values at 0.0."""
    return NormalizedAttributes(
        image_id="test456",
        composition=0.0,
        subject_strength=0.0,
        visual_appeal=0.0,
        sharpness=0.0,
        exposure_balance=0.0,
        noise_level=0.0,
    )


class TestScoringReducer:
    """Tests for ScoringReducer."""

    def test_perfect_score(
        self, reducer: ScoringReducer, perfect_attributes: NormalizedAttributes
    ):
        """Perfect attributes should yield score of 100."""
        result = reducer.compute_scores("test123", "test/image.jpg", perfect_attributes)
        assert result.final_score == 100.0
        assert result.technical_score == 1.0
        assert result.aesthetic_score == 1.0

    def test_zero_score(
        self, reducer: ScoringReducer, poor_attributes: NormalizedAttributes
    ):
        """Zero attributes should yield low score with threshold penalties."""
        result = reducer.compute_scores("test456", "test/image.jpg", poor_attributes)
        # Score should be very low due to threshold penalties
        assert result.final_score < 50.0
        assert result.technical_score == 0.0
        assert result.aesthetic_score == 0.0

    def test_mixed_score(self, reducer: ScoringReducer):
        """Mixed attributes should yield intermediate score."""
        attrs = NormalizedAttributes(
            image_id="test789",
            composition=0.8,
            subject_strength=0.7,
            visual_appeal=0.6,
            sharpness=0.9,
            exposure_balance=0.8,
            noise_level=0.7,
        )
        result = reducer.compute_scores("test789", "test/image.jpg", attrs)
        assert 50.0 < result.final_score < 90.0

    def test_sharpness_threshold(self, reducer: ScoringReducer):
        """Low sharpness should apply penalty."""
        # Good image with low sharpness
        attrs = NormalizedAttributes(
            image_id="test_sharp",
            composition=0.9,
            subject_strength=0.9,
            visual_appeal=0.9,
            sharpness=0.1,  # Below threshold
            exposure_balance=0.9,
            noise_level=0.9,
        )
        result = reducer.compute_scores("test_sharp", "test/image.jpg", attrs)
        # Score should be penalized
        assert result.final_score < 90.0

    def test_contributions_sum(
        self, reducer: ScoringReducer, perfect_attributes: NormalizedAttributes
    ):
        """Contributions should sum to approximately 1.0 for perfect attributes."""
        result = reducer.compute_scores("test123", "test/image.jpg", perfect_attributes)
        total = sum(result.contributions.values())
        assert 0.99 <= total <= 1.01

    def test_contributions_keys(
        self, reducer: ScoringReducer, perfect_attributes: NormalizedAttributes
    ):
        """All attribute keys should be present in contributions."""
        result = reducer.compute_scores("test123", "test/image.jpg", perfect_attributes)
        expected_keys = {
            "composition",
            "subject_strength",
            "visual_appeal",
            "sharpness",
            "exposure_balance",
            "noise_level",
        }
        assert set(result.contributions.keys()) == expected_keys

    def test_determinism(
        self, reducer: ScoringReducer, perfect_attributes: NormalizedAttributes
    ):
        """Same inputs should yield identical outputs."""
        result1 = reducer.compute_scores(
            "test123", "test/image.jpg", perfect_attributes
        )
        result2 = reducer.compute_scores(
            "test123", "test/image.jpg", perfect_attributes
        )
        assert result1.final_score == result2.final_score
        assert result1.contributions == result2.contributions
