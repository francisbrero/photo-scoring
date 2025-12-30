"""Configuration schema for scoring."""

from pydantic import BaseModel, Field, model_validator


class ModelConfig(BaseModel):
    """Vision model configuration."""

    name: str = Field(default="anthropic/claude-3.5-sonnet")
    version: str = Field(default="20241022")


class AestheticWeights(BaseModel):
    """Weights for aesthetic attributes."""

    composition: float = Field(default=0.4, ge=0.0, le=1.0)
    subject_strength: float = Field(default=0.35, ge=0.0, le=1.0)
    visual_appeal: float = Field(default=0.25, ge=0.0, le=1.0)


class TechnicalWeights(BaseModel):
    """Weights for technical attributes."""

    sharpness: float = Field(default=0.4, ge=0.0, le=1.0)
    exposure_balance: float = Field(default=0.35, ge=0.0, le=1.0)
    noise_level: float = Field(default=0.25, ge=0.0, le=1.0)


class Weights(BaseModel):
    """All attribute weights."""

    aesthetic: AestheticWeights = Field(default_factory=AestheticWeights)
    technical: TechnicalWeights = Field(default_factory=TechnicalWeights)


class CategoryWeights(BaseModel):
    """Weights for category aggregation."""

    aesthetic: float = Field(default=0.6, ge=0.0, le=1.0)
    technical: float = Field(default=0.4, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_sum(self) -> "CategoryWeights":
        total = self.aesthetic + self.technical
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Category weights must sum to 1.0, got {total}")
        return self


class Thresholds(BaseModel):
    """Hard thresholds for scoring penalties."""

    sharpness_min: float = Field(default=0.2, ge=0.0, le=1.0)
    exposure_min: float = Field(default=0.1, ge=0.0, le=1.0)


class ScoringConfig(BaseModel):
    """Complete scoring configuration."""

    version: str = Field(default="1.0")
    model: ModelConfig = Field(default_factory=ModelConfig)
    weights: Weights = Field(default_factory=Weights)
    category_weights: CategoryWeights = Field(default_factory=CategoryWeights)
    thresholds: Thresholds = Field(default_factory=Thresholds)
