"""EXIF metadata extraction."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

logger = logging.getLogger(__name__)


def _convert_to_degrees(value: tuple) -> float:
    """Convert GPS coordinates from EXIF format to decimal degrees."""
    d, m, s = value
    return float(d) + float(m) / 60.0 + float(s) / 3600.0


def _extract_gps_info(exif: dict[str, Any]) -> dict[str, Any] | None:
    """Extract GPS coordinates from EXIF data.

    Returns:
        Dictionary with 'latitude' and 'longitude' as floats, or None.
    """
    if "GPSInfo" not in exif:
        return None

    gps_info = exif["GPSInfo"]

    # Convert GPS tag IDs to names
    gps_data: dict[str, Any] = {}
    for tag_id, value in gps_info.items():
        tag_name = GPSTAGS.get(tag_id, str(tag_id))
        gps_data[tag_name] = value

    # Check for required fields
    if not all(k in gps_data for k in ["GPSLatitude", "GPSLongitude", "GPSLatitudeRef", "GPSLongitudeRef"]):
        return None

    try:
        lat = _convert_to_degrees(gps_data["GPSLatitude"])
        lon = _convert_to_degrees(gps_data["GPSLongitude"])

        # Apply hemisphere reference
        if gps_data["GPSLatitudeRef"] == "S":
            lat = -lat
        if gps_data["GPSLongitudeRef"] == "W":
            lon = -lon

        return {"latitude": lat, "longitude": lon}
    except (TypeError, ValueError, ZeroDivisionError) as e:
        logger.debug(f"Failed to parse GPS coordinates: {e}")
        return None


def extract_exif(file_path: Path) -> dict[str, Any] | None:
    """Extract basic EXIF metadata from an image file.

    Args:
        file_path: Path to the image file.

    Returns:
        Dictionary with extracted metadata, or None if extraction fails.
        Keys: timestamp, camera_make, camera_model, lens_model, latitude, longitude
    """
    try:
        with Image.open(file_path) as img:
            exif_data = img._getexif()
            if exif_data is None:
                return None

            # Build a tag name -> value mapping
            exif: dict[str, Any] = {}
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, str(tag_id))
                exif[tag_name] = value

            result: dict[str, Any] = {}

            # Timestamp
            if "DateTimeOriginal" in exif:
                try:
                    result["timestamp"] = datetime.strptime(
                        exif["DateTimeOriginal"], "%Y:%m:%d %H:%M:%S"
                    )
                except ValueError:
                    pass

            # Camera info
            if "Make" in exif:
                result["camera_make"] = str(exif["Make"]).strip()
            if "Model" in exif:
                result["camera_model"] = str(exif["Model"]).strip()

            # Lens info
            if "LensModel" in exif:
                result["lens_model"] = str(exif["LensModel"]).strip()

            # GPS coordinates
            gps = _extract_gps_info(exif)
            if gps:
                result["latitude"] = gps["latitude"]
                result["longitude"] = gps["longitude"]

            return result if result else None

    except Exception as e:
        logger.debug(f"Failed to extract EXIF from {file_path}: {e}")
        return None
