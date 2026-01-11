"""Image discovery and metadata extraction.

This module provides functions for discovering images in directories
and extracting EXIF metadata.

Main exports:
- discover_images: Recursively find images in a directory
- extract_exif: Extract EXIF metadata from an image
- DEFAULT_EXTENSIONS: Default supported image extensions
"""

from photo_score.ingestion.discover import discover_images, DEFAULT_EXTENSIONS
from photo_score.ingestion.metadata import extract_exif

__all__ = ["discover_images", "extract_exif", "DEFAULT_EXTENSIONS"]
