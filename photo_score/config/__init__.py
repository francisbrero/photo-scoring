"""Configuration loading and validation.

This module provides configuration loading from YAML files
and validation of configuration values.

Main exports:
- load_config: Load configuration from a YAML file
- get_default_config: Get the default configuration
- ScoringConfig: Configuration data model
"""

from photo_score.config.loader import load_config, get_default_config
from photo_score.config.schema import ScoringConfig

__all__ = ["load_config", "get_default_config", "ScoringConfig"]
