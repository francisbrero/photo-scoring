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

    # Explanation and recommendations
    explanation: str = ""
    improvements: list[str] = field(default_factory=list)


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

    def generate_explanation(self, result: CompositeResult) -> str:
        """Generate a human-readable explanation of the score.

        Highlights the most impactful positive and negative attributes.
        """
        # Collect all scores with their names and values
        scores = [
            ("composition", result.composition, "aesthetic"),
            ("subject strength", result.subject_strength, "aesthetic"),
            ("visual appeal", result.visual_appeal, "aesthetic"),
            ("sharpness", result.sharpness, "technical"),
            ("exposure", result.exposure, "technical"),
            ("noise control", result.noise_level, "technical"),
        ]

        # Sort by value
        sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)

        # Find strengths (>= 0.65) and weaknesses (< 0.5)
        strengths = [(name, val) for name, val, _ in sorted_scores if val >= 0.65]
        weaknesses = [(name, val) for name, val, _ in sorted_scores if val < 0.5]

        parts = []

        # Score tier
        if result.final_score >= 85:
            parts.append("Excellent shot.")
        elif result.final_score >= 70:
            parts.append("Strong image.")
        elif result.final_score >= 55:
            parts.append("Solid photo.")
        elif result.final_score >= 40:
            parts.append("Average snapshot.")
        else:
            parts.append("Needs improvement.")

        # Top strengths
        if strengths:
            top_strengths = strengths[:2]
            strength_text = " and ".join([s[0] for s in top_strengths])
            parts.append(f"Stands out for its {strength_text}.")

        # Weaknesses
        if weaknesses:
            worst = min(weaknesses, key=lambda x: x[1])
            if worst[1] < 0.35:
                parts.append(f"Significantly held back by weak {worst[0]}.")
            else:
                parts.append(f"Could improve {worst[0]}.")

        # Aesthetic vs technical balance
        aes_avg = (result.composition + result.subject_strength + result.visual_appeal) / 3
        tech_avg = (result.sharpness + result.exposure + result.noise_level) / 3

        if tech_avg - aes_avg > 0.15:
            parts.append("Technically proficient but lacks artistic impact.")
        elif aes_avg - tech_avg > 0.15:
            parts.append("Good creative vision, but technical execution could be better.")

        return " ".join(parts)

    def generate_improvements(self, result: CompositeResult) -> list[str]:
        """Generate actionable improvement recommendations.

        Provides specific editing and composition suggestions based on scores and features.
        """
        improvements = []
        features = result.features

        # Composition improvements
        if result.composition < 0.5:
            if features.subject_position == "center":
                improvements.append(
                    "Try the rule of thirds: crop to place your subject off-center, "
                    "at one of the intersection points of a 3x3 grid."
                )
            elif features.background == "busy":
                improvements.append(
                    "Simplify the composition by cropping out distracting background elements."
                )
            else:
                improvements.append(
                    "Consider reframing: look for leading lines, natural frames, "
                    "or a cleaner background to strengthen the composition."
                )

        # Subject strength improvements
        if result.subject_strength < 0.5:
            if features.background == "busy":
                improvements.append(
                    "Make the subject pop: try increasing contrast or saturation on the subject, "
                    "or desaturate/blur the background slightly."
                )
            if features.depth_of_field == "deep":
                improvements.append(
                    "Use a wider aperture next time to blur the background "
                    "and draw attention to your subject."
                )
            if not features.main_subject:
                improvements.append(
                    "The image lacks a clear focal point. When shooting, "
                    "decide what story you want to tell and make that element prominent."
                )

        # Visual appeal improvements
        if result.visual_appeal < 0.5:
            if features.color_palette == "muted":
                improvements.append(
                    "Boost vibrancy: increase saturation slightly or add warmth "
                    "to make colors more engaging."
                )
            if features.lighting == "natural_harsh":
                improvements.append(
                    "Harsh lighting creates unflattering shadows. "
                    "Try shooting during golden hour or use fill flash."
                )
            if features.lighting == "artificial":
                improvements.append(
                    "Adjust white balance to correct color cast from artificial lighting."
                )

        # Sharpness improvements
        if result.sharpness < 0.5:
            if "blur" in features.technical_issues or "motion" in str(features.technical_issues).lower():
                improvements.append(
                    "Image shows motion blur. Use a faster shutter speed "
                    "or enable image stabilization. Consider a tripod for low light."
                )
            else:
                improvements.append(
                    "Apply subtle sharpening in post-processing. "
                    "Use the 'Unsharp Mask' or 'Clarity' slider carefully."
                )

        # Exposure improvements
        if result.exposure < 0.5:
            if "overexposed" in str(features.technical_issues).lower():
                improvements.append(
                    "Highlights are blown out. Reduce exposure in post, "
                    "or use the 'Highlights' slider to recover detail."
                )
            elif "underexposed" in str(features.technical_issues).lower():
                improvements.append(
                    "Image is too dark. Increase exposure and lift shadows, "
                    "but watch for increased noise."
                )
            else:
                improvements.append(
                    "Fine-tune exposure: adjust the histogram so highlights "
                    "don't clip and shadows retain detail."
                )

        # Noise improvements
        if result.noise_level < 0.5:
            improvements.append(
                "Visible noise degrades quality. Apply noise reduction in post-processing, "
                "or next time use a lower ISO setting with better lighting."
            )

        # Scene-specific improvements
        if features.scene_type == "portrait" and features.lighting != "natural_soft":
            improvements.append(
                "For portraits, soft diffused lighting is most flattering. "
                "Try shooting near a window or use a reflector."
            )

        if features.scene_type == "landscape" and features.time_of_day == "midday":
            improvements.append(
                "Midday light is harsh for landscapes. "
                "Golden hour (sunrise/sunset) provides warmer, more dramatic lighting."
            )

        # Tilted horizon
        if "tilted" in str(features.technical_issues).lower():
            improvements.append(
                "Straighten the horizon using the crop/rotate tool."
            )

        # If no specific improvements, give general advice
        if not improvements:
            if result.final_score >= 70:
                improvements.append(
                    "This is already a strong image. Minor tweaks like "
                    "subtle contrast adjustments or selective sharpening could enhance it further."
                )
            else:
                improvements.append(
                    "Focus on one element to improve: either strengthen the subject, "
                    "simplify the background, or improve the lighting."
                )

        return improvements[:3]  # Return top 3 most relevant improvements

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

        # Generate explanation and improvements
        result.explanation = self.generate_explanation(result)
        result.improvements = self.generate_improvements(result)

        return result

    def close(self) -> None:
        self.client.close()
