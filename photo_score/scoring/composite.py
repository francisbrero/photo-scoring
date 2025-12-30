"""Composite scoring system using multiple vision models."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from photo_score.inference.client import OpenRouterClient, OpenRouterError
from photo_score.inference.prompts_v2 import (
    FEATURE_EXTRACTION_PROMPT,
    AESTHETIC_SCORING_PROMPT,
    TECHNICAL_SCORING_PROMPT,
    METADATA_PROMPT,
)

logger = logging.getLogger(__name__)

# Model configuration for composite scoring
MODELS = {
    "feature_extraction": "mistralai/pixtral-12b",      # $0.10/M - cheap, detailed
    "aesthetic_scorers": [
        ("qwen/qwen2.5-vl-72b-instruct", 0.35),         # $0.07/M - cheapest
        ("openai/gpt-4o-mini", 0.35),                    # $0.15/M - good calibration
        ("google/gemini-2.5-flash", 0.30),              # $0.30/M - fast
    ],
    "technical_scorers": [
        ("qwen/qwen2.5-vl-72b-instruct", 0.35),
        ("openai/gpt-4o-mini", 0.35),
        ("google/gemini-2.5-flash", 0.30),
    ],
    "metadata": "mistralai/pixtral-12b",                # $0.10/M - cheap
}


@dataclass
class FeatureExtraction:
    """Extracted features from an image."""
    scene_type: str = ""
    main_subject: str = ""
    subject_position: str = ""
    background: str = ""
    lighting: str = ""
    color_palette: str = ""
    depth_of_field: str = ""
    motion: str = ""
    human_presence: str = ""
    text_or_signs: bool = False
    weather_visible: str = ""
    time_of_day: str = ""
    technical_issues: list[str] = field(default_factory=list)
    notable_elements: list[str] = field(default_factory=list)
    estimated_location_type: str = ""
    raw: dict = field(default_factory=dict)


@dataclass
class ModelScore:
    """Score from a single model."""
    model_id: str
    composition: float = 0.0
    subject_strength: float = 0.0
    visual_appeal: float = 0.0
    sharpness: float = 0.0
    exposure: float = 0.0
    noise_level: float = 0.0
    reasoning: str = ""
    success: bool = True
    error: str = ""


@dataclass
class CompositeResult:
    """Complete composite scoring result."""
    image_path: str

    # Feature extraction
    features: FeatureExtraction = field(default_factory=FeatureExtraction)

    # Individual model scores
    aesthetic_scores: list[ModelScore] = field(default_factory=list)
    technical_scores: list[ModelScore] = field(default_factory=list)

    # Weighted composite scores
    composition: float = 0.0
    subject_strength: float = 0.0
    visual_appeal: float = 0.0
    sharpness: float = 0.0
    exposure: float = 0.0
    noise_level: float = 0.0

    # Final scores
    aesthetic_score: float = 0.0
    technical_score: float = 0.0
    final_score: float = 0.0

    # Metadata
    description: str = ""
    location_name: str = ""
    location_country: str = ""


class CompositeScorer:
    """Score images using multiple models and combine results."""

    def __init__(self, api_key: str | None = None):
        self.client = OpenRouterClient(api_key=api_key)

    def extract_features(self, image_path: Path) -> FeatureExtraction:
        """Extract detailed features using Pixtral."""
        try:
            result = self.client._call_api(
                image_path,
                FEATURE_EXTRACTION_PROMPT,
                model=MODELS["feature_extraction"]
            )
            return FeatureExtraction(
                scene_type=result.get("scene_type", ""),
                main_subject=result.get("main_subject", ""),
                subject_position=result.get("subject_position", ""),
                background=result.get("background", ""),
                lighting=result.get("lighting", ""),
                color_palette=result.get("color_palette", ""),
                depth_of_field=result.get("depth_of_field", ""),
                motion=result.get("motion", ""),
                human_presence=result.get("human_presence", ""),
                text_or_signs=result.get("text_or_signs", False),
                weather_visible=result.get("weather_visible", ""),
                time_of_day=result.get("time_of_day", ""),
                technical_issues=result.get("technical_issues", []),
                notable_elements=result.get("notable_elements", []),
                estimated_location_type=result.get("estimated_location_type", ""),
                raw=result,
            )
        except OpenRouterError as e:
            logger.warning(f"Feature extraction failed: {e}")
            return FeatureExtraction()

    def get_aesthetic_score(self, image_path: Path, model_id: str) -> ModelScore:
        """Get aesthetic score from a single model."""
        score = ModelScore(model_id=model_id)
        try:
            result = self.client._call_api(
                image_path,
                AESTHETIC_SCORING_PROMPT,
                model=model_id
            )
            score.composition = float(result.get("composition", 0))
            score.subject_strength = float(result.get("subject_strength", 0))
            score.visual_appeal = float(result.get("visual_appeal", 0))
            score.reasoning = result.get("reasoning", "")
        except OpenRouterError as e:
            score.success = False
            score.error = str(e)
            logger.warning(f"Aesthetic scoring failed for {model_id}: {e}")
        return score

    def get_technical_score(self, image_path: Path, model_id: str) -> ModelScore:
        """Get technical score from a single model."""
        score = ModelScore(model_id=model_id)
        try:
            result = self.client._call_api(
                image_path,
                TECHNICAL_SCORING_PROMPT,
                model=model_id
            )
            score.sharpness = float(result.get("sharpness", 0))
            score.exposure = float(result.get("exposure", 0))
            score.noise_level = float(result.get("noise_level", 0))
            score.reasoning = result.get("reasoning", "")
        except OpenRouterError as e:
            score.success = False
            score.error = str(e)
            logger.warning(f"Technical scoring failed for {model_id}: {e}")
        return score

    def get_metadata(self, image_path: Path) -> tuple[str, str, str]:
        """Get description and location using Pixtral."""
        try:
            result = self.client._call_api(
                image_path,
                METADATA_PROMPT,
                model=MODELS["metadata"]
            )
            return (
                result.get("description", ""),
                result.get("location_name"),
                result.get("location_country"),
            )
        except OpenRouterError as e:
            logger.warning(f"Metadata extraction failed: {e}")
            return ("", None, None)

    def compute_weighted_scores(self, result: CompositeResult) -> None:
        """Compute weighted composite scores from individual model scores."""
        # Aesthetic scores
        aesthetic_scorers = MODELS["aesthetic_scorers"]
        total_weight = 0.0

        for score in result.aesthetic_scores:
            if not score.success:
                continue
            # Find weight for this model
            weight = next(
                (w for model_id, w in aesthetic_scorers if model_id == score.model_id),
                0.0
            )
            result.composition += score.composition * weight
            result.subject_strength += score.subject_strength * weight
            result.visual_appeal += score.visual_appeal * weight
            total_weight += weight

        if total_weight > 0:
            result.composition /= total_weight
            result.subject_strength /= total_weight
            result.visual_appeal /= total_weight

        # Technical scores
        technical_scorers = MODELS["technical_scorers"]
        total_weight = 0.0

        for score in result.technical_scores:
            if not score.success:
                continue
            weight = next(
                (w for model_id, w in technical_scorers if model_id == score.model_id),
                0.0
            )
            result.sharpness += score.sharpness * weight
            result.exposure += score.exposure * weight
            result.noise_level += score.noise_level * weight
            total_weight += weight

        if total_weight > 0:
            result.sharpness /= total_weight
            result.exposure /= total_weight
            result.noise_level /= total_weight

        # Compute final scores
        result.aesthetic_score = (
            result.composition * 0.4 +
            result.subject_strength * 0.35 +
            result.visual_appeal * 0.25
        )
        result.technical_score = (
            result.sharpness * 0.4 +
            result.exposure * 0.35 +
            result.noise_level * 0.25
        )
        result.final_score = (
            result.aesthetic_score * 0.6 +
            result.technical_score * 0.4
        ) * 100

    def score_image(self, image_path: Path, include_features: bool = True) -> CompositeResult:
        """Score a single image using the composite system.

        API calls made:
        - 1x Pixtral for feature extraction (optional)
        - 3x aesthetic scoring (Qwen, GPT-4o-mini, Gemini)
        - 3x technical scoring (Qwen, GPT-4o-mini, Gemini)
        - 1x Pixtral for metadata

        Total: 8 API calls per image (7 if features disabled)
        """
        result = CompositeResult(image_path=str(image_path.name))

        # Feature extraction (optional but useful for analysis)
        if include_features:
            logger.info(f"Extracting features: {image_path.name}")
            result.features = self.extract_features(image_path)

        # Aesthetic scoring from multiple models
        for model_id, weight in MODELS["aesthetic_scorers"]:
            logger.info(f"Aesthetic scoring ({model_id}): {image_path.name}")
            score = self.get_aesthetic_score(image_path, model_id)
            result.aesthetic_scores.append(score)

        # Technical scoring from multiple models
        for model_id, weight in MODELS["technical_scorers"]:
            logger.info(f"Technical scoring ({model_id}): {image_path.name}")
            score = self.get_technical_score(image_path, model_id)
            result.technical_scores.append(score)

        # Metadata
        logger.info(f"Extracting metadata: {image_path.name}")
        desc, loc_name, loc_country = self.get_metadata(image_path)
        result.description = desc
        result.location_name = loc_name or ""
        result.location_country = loc_country or ""

        # Compute weighted scores
        self.compute_weighted_scores(result)

        return result

    def close(self) -> None:
        self.client.close()
