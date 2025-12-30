"""Tests for explanation generation."""

import pytest

from photo_score.config.schema import ScoringConfig
from photo_score.scoring.explanations import ExplanationGenerator
from photo_score.storage.models import NormalizedAttributes


@pytest.fixture
def default_config() -> ScoringConfig:
    """Default scoring configuration."""
    return ScoringConfig()


@pytest.fixture
def generator(default_config: ScoringConfig) -> ExplanationGenerator:
    """Explanation generator with default config."""
    return ExplanationGenerator(default_config)


class TestExplanationGenerator:
    """Tests for ExplanationGenerator."""

    def test_high_score_explanation(self, generator: ExplanationGenerator):
        """High score should mention 'scores highly'."""
        attrs = NormalizedAttributes(
            image_id="test",
            composition=0.9,
            subject_strength=0.9,
            visual_appeal=0.9,
            sharpness=0.9,
            exposure_balance=0.9,
            noise_level=0.9,
        )
        contributions = {
            "composition": 0.24,
            "subject_strength": 0.21,
            "visual_appeal": 0.15,
            "sharpness": 0.16,
            "exposure_balance": 0.14,
            "noise_level": 0.10,
        }
        explanation = generator.generate(attrs, contributions, 85.0)
        assert "scores highly" in explanation

    def test_low_score_explanation(self, generator: ExplanationGenerator):
        """Low score should mention 'scores lower'."""
        attrs = NormalizedAttributes(
            image_id="test",
            composition=0.3,
            subject_strength=0.3,
            visual_appeal=0.3,
            sharpness=0.3,
            exposure_balance=0.3,
            noise_level=0.3,
        )
        contributions = {
            "composition": 0.08,
            "subject_strength": 0.07,
            "visual_appeal": 0.05,
            "sharpness": 0.05,
            "exposure_balance": 0.04,
            "noise_level": 0.03,
        }
        explanation = generator.generate(attrs, contributions, 35.0)
        assert "scores lower" in explanation

    def test_penalty_mentioned(self, generator: ExplanationGenerator):
        """Weak attributes should be mentioned as penalties."""
        attrs = NormalizedAttributes(
            image_id="test",
            composition=0.9,
            subject_strength=0.9,
            visual_appeal=0.9,
            sharpness=0.2,  # Weak
            exposure_balance=0.9,
            noise_level=0.9,
        )
        contributions = {
            "composition": 0.24,
            "subject_strength": 0.21,
            "visual_appeal": 0.15,
            "sharpness": 0.03,
            "exposure_balance": 0.14,
            "noise_level": 0.10,
        }
        explanation = generator.generate(attrs, contributions, 70.0)
        assert "penalized" in explanation.lower()

    def test_determinism(self, generator: ExplanationGenerator):
        """Same inputs should yield identical explanations."""
        attrs = NormalizedAttributes(
            image_id="test",
            composition=0.8,
            subject_strength=0.7,
            visual_appeal=0.6,
            sharpness=0.8,
            exposure_balance=0.7,
            noise_level=0.6,
        )
        contributions = {
            "composition": 0.19,
            "subject_strength": 0.15,
            "visual_appeal": 0.09,
            "sharpness": 0.13,
            "exposure_balance": 0.10,
            "noise_level": 0.06,
        }
        exp1 = generator.generate(attrs, contributions, 70.0)
        exp2 = generator.generate(attrs, contributions, 70.0)
        assert exp1 == exp2

    def test_top_contributors_mentioned(self, generator: ExplanationGenerator):
        """Top contributors should be mentioned in explanation."""
        attrs = NormalizedAttributes(
            image_id="test",
            composition=0.95,  # Highest aesthetic
            subject_strength=0.8,
            visual_appeal=0.7,
            sharpness=0.9,  # Highest technical
            exposure_balance=0.8,
            noise_level=0.7,
        )
        contributions = {
            "composition": 0.23,  # Highest
            "subject_strength": 0.17,
            "visual_appeal": 0.11,
            "sharpness": 0.14,
            "exposure_balance": 0.11,
            "noise_level": 0.07,
        }
        explanation = generator.generate(attrs, contributions, 80.0)
        # Should mention composition as it has highest contribution
        assert "composition" in explanation
