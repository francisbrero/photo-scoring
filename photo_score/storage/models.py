"""Data models for photo scoring."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class ImageRecord(BaseModel):
    """Represents a discovered image file."""

    image_id: str = Field(description="SHA256 hash of file contents")
    file_path: Path = Field(description="Absolute path to the image file")
    relative_path: str = Field(description="Path relative to input directory")
    filename: str = Field(description="Image filename")
    discovered_at: datetime = Field(default_factory=datetime.now)


class RawInferenceResult(BaseModel):
    """Raw response from vision model inference."""

    image_id: str
    model_name: str
    model_version: str
    raw_response: dict
    created_at: datetime = Field(default_factory=datetime.now)


class NormalizedAttributes(BaseModel):
    """Normalized image attributes, all values in [0, 1] range."""

    image_id: str

    # Aesthetic attributes
    composition: float = Field(ge=0.0, le=1.0)
    subject_strength: float = Field(ge=0.0, le=1.0)
    visual_appeal: float = Field(ge=0.0, le=1.0)

    # Technical attributes
    sharpness: float = Field(ge=0.0, le=1.0)
    exposure_balance: float = Field(ge=0.0, le=1.0)
    noise_level: float = Field(ge=0.0, le=1.0)

    # Metadata
    model_name: Optional[str] = None
    model_version: Optional[str] = None


class ImageMetadata(BaseModel):
    """Metadata extracted from an image."""

    # From EXIF
    date_taken: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # From vision model
    description: Optional[str] = None
    location_name: Optional[str] = None
    location_country: Optional[str] = None


class ScoringResult(BaseModel):
    """Result of scoring an image."""

    image_id: str
    image_path: str
    final_score: float = Field(ge=0.0, le=100.0)
    technical_score: float = Field(ge=0.0, le=1.0)
    aesthetic_score: float = Field(ge=0.0, le=1.0)
    attributes: NormalizedAttributes
    contributions: dict[str, float]
    explanation: str = ""
    metadata: Optional[ImageMetadata] = None
