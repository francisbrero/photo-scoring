"""SQLite cache and data models.

This module provides the caching layer for inference results
and the data models used throughout the application.

Main exports:
- Cache: SQLite-based cache for inference results
- NormalizedAttributes: Normalized attribute values from inference
- ScoringResult: Complete scoring result with contributions
- ImageMetadata: EXIF and vision-derived metadata
"""

from photo_score.storage.cache import Cache
from photo_score.storage.models import (
    NormalizedAttributes,
    ScoringResult,
    ImageMetadata,
    RawInferenceResult,
)

__all__ = [
    "Cache",
    "NormalizedAttributes",
    "ScoringResult",
    "ImageMetadata",
    "RawInferenceResult",
]
