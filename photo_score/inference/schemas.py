"""Response schemas for vision model inference."""

from typing import Optional

from pydantic import BaseModel, Field


class AestheticResponse(BaseModel):
    """Expected response format for aesthetic analysis."""

    composition: float = Field(
        ge=0.0, le=1.0, description="Quality of framing and visual balance"
    )
    subject_strength: float = Field(
        ge=0.0, le=1.0, description="Clarity and prominence of main subject"
    )
    visual_appeal: float = Field(
        ge=0.0, le=1.0, description="Overall visual attractiveness"
    )


class TechnicalResponse(BaseModel):
    """Expected response format for technical analysis."""

    sharpness: float = Field(
        ge=0.0, le=1.0, description="Image sharpness and focus quality"
    )
    exposure_balance: float = Field(
        ge=0.0, le=1.0, description="Proper exposure without over/underexposure"
    )
    noise_level: float = Field(
        ge=0.0,
        le=1.0,
        description="Absence of noise (1.0 = no noise, 0.0 = very noisy)",
    )


class MetadataResponse(BaseModel):
    """Expected response format for metadata analysis."""

    description: str = Field(description="1-3 sentence description of the photo")
    location_name: Optional[str] = Field(
        default=None, description="City, region, or landmark name"
    )
    location_country: Optional[str] = Field(default=None, description="Country name")
