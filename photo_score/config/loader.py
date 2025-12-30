"""Configuration loading from YAML files."""

from pathlib import Path

import yaml

from photo_score.config.schema import ScoringConfig


def load_config(path: Path) -> ScoringConfig:
    """Load and validate scoring configuration from YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    return ScoringConfig.model_validate(data)


def get_default_config() -> ScoringConfig:
    """Return default scoring configuration."""
    return ScoringConfig()
