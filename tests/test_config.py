"""Tests for configuration loading and validation."""

import tempfile
from pathlib import Path

import pytest
import yaml

from photo_score.config.loader import get_default_config, load_config
from photo_score.config.schema import ScoringConfig


class TestConfigSchema:
    """Tests for configuration schema validation."""

    def test_default_config(self):
        """Default config should be valid."""
        config = get_default_config()
        assert config.version == "1.0"
        assert config.model.name == "anthropic/claude-3.5-sonnet"

    def test_category_weights_sum_to_one(self):
        """Category weights must sum to 1.0."""
        config = get_default_config()
        total = config.category_weights.aesthetic + config.category_weights.technical
        assert abs(total - 1.0) < 0.001

    def test_category_weights_invalid(self):
        """Invalid category weights should raise error."""
        with pytest.raises(ValueError):
            ScoringConfig(
                category_weights={
                    "aesthetic": 0.5,
                    "technical": 0.3,
                }  # Doesn't sum to 1
            )

    def test_weight_bounds(self):
        """Weights should be between 0 and 1."""
        config = get_default_config()

        # Aesthetic weights
        assert 0.0 <= config.weights.aesthetic.composition <= 1.0
        assert 0.0 <= config.weights.aesthetic.subject_strength <= 1.0
        assert 0.0 <= config.weights.aesthetic.visual_appeal <= 1.0

        # Technical weights
        assert 0.0 <= config.weights.technical.sharpness <= 1.0
        assert 0.0 <= config.weights.technical.exposure_balance <= 1.0
        assert 0.0 <= config.weights.technical.noise_level <= 1.0


class TestConfigLoader:
    """Tests for configuration file loading."""

    def test_load_valid_config(self):
        """Valid YAML config should load successfully."""
        config_data = {
            "version": "2.0",
            "model": {
                "name": "test/model",
                "version": "1.0",
            },
            "weights": {
                "aesthetic": {
                    "composition": 0.5,
                    "subject_strength": 0.3,
                    "visual_appeal": 0.2,
                },
                "technical": {
                    "sharpness": 0.5,
                    "exposure_balance": 0.3,
                    "noise_level": 0.2,
                },
            },
            "category_weights": {
                "aesthetic": 0.7,
                "technical": 0.3,
            },
            "thresholds": {
                "sharpness_min": 0.3,
                "exposure_min": 0.2,
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            f.flush()

            config = load_config(Path(f.name))
            assert config.version == "2.0"
            assert config.model.name == "test/model"
            assert config.weights.aesthetic.composition == 0.5
            assert config.category_weights.aesthetic == 0.7

    def test_load_partial_config(self):
        """Partial config should use defaults for missing fields."""
        config_data = {
            "version": "1.5",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            f.flush()

            config = load_config(Path(f.name))
            assert config.version == "1.5"
            # Should use default model
            assert config.model.name == "anthropic/claude-3.5-sonnet"

    def test_load_empty_config(self):
        """Empty config should use all defaults."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("{}")
            f.flush()

            config = load_config(Path(f.name))
            default = get_default_config()
            assert config.model.name == default.model.name
