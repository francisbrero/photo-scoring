"""Deterministic explanation generation for image scores."""

from photo_score.config.schema import ScoringConfig
from photo_score.storage.models import NormalizedAttributes

# Human-readable attribute names
ATTR_NAMES = {
    "composition": "composition",
    "subject_strength": "subject clarity",
    "visual_appeal": "visual appeal",
    "sharpness": "sharpness",
    "exposure_balance": "exposure",
    "noise_level": "low noise",
}


class ExplanationGenerator:
    """Generates deterministic explanations for image scores."""

    def __init__(self, config: ScoringConfig):
        """Initialize generator with scoring configuration."""
        self.config = config

    def generate(
        self,
        attributes: NormalizedAttributes,
        contributions: dict[str, float],
        final_score: float,
    ) -> str:
        """Generate explanation for an image score.

        Args:
            attributes: Normalized attribute values.
            contributions: Per-attribute contribution values.
            final_score: Final computed score (0-100).

        Returns:
            Concise explanation string.
        """
        attr_values = {
            "composition": attributes.composition,
            "subject_strength": attributes.subject_strength,
            "visual_appeal": attributes.visual_appeal,
            "sharpness": attributes.sharpness,
            "exposure_balance": attributes.exposure_balance,
            "noise_level": attributes.noise_level,
        }

        # Sort by value to find strengths and weaknesses
        sorted_attrs = sorted(attr_values.items(), key=lambda x: x[1], reverse=True)

        # Find strong attributes (>= 0.7) and weak ones (< 0.5)
        strong = [(a, v) for a, v in sorted_attrs if v >= 0.7]
        weak = [(a, v) for a, v in sorted_attrs if v < 0.5]

        parts = []

        # Score tier description
        if final_score >= 70:
            tier = "Near-publishable"
        elif final_score >= 55:
            tier = "Competent but unremarkable"
        elif final_score >= 40:
            tier = "Tourist-level"
        else:
            tier = "Flawed"

        # Build explanation
        if strong:
            strong_names = [ATTR_NAMES[a] for a, _ in strong[:2]]
            if len(strong_names) == 2:
                parts.append(f"{tier}. Strong {strong_names[0]} and {strong_names[1]}.")
            else:
                parts.append(f"{tier}. Strong {strong_names[0]}.")
        else:
            parts.append(f"{tier}. No standout qualities.")

        # Weaknesses
        if weak:
            weak_sorted = sorted(weak, key=lambda x: x[1])
            weakest = weak_sorted[0]
            weak_name = ATTR_NAMES[weakest[0]]
            if weakest[1] < 0.35:
                parts.append(f"Weak {weak_name} hurts the image.")
            else:
                parts.append(f"{weak_name.capitalize()} is mediocre.")

        # Aesthetic vs technical gap insight
        aes_avg = (
            attributes.composition
            + attributes.subject_strength
            + attributes.visual_appeal
        ) / 3
        tech_avg = (
            attributes.sharpness + attributes.exposure_balance + attributes.noise_level
        ) / 3

        if tech_avg - aes_avg > 0.15:
            parts.append("Technically fine but aesthetically weak.")
        elif aes_avg - tech_avg > 0.15:
            parts.append("Good eye, execution could improve.")

        return " ".join(parts)

    def _get_highest_weight_attr(self) -> str | None:
        """Find attribute with highest effective weight."""
        aes_weights = self.config.weights.aesthetic
        tech_weights = self.config.weights.technical
        cat_weights = self.config.category_weights

        effective = {
            "composition": aes_weights.composition * cat_weights.aesthetic,
            "subject_strength": aes_weights.subject_strength * cat_weights.aesthetic,
            "visual_appeal": aes_weights.visual_appeal * cat_weights.aesthetic,
            "sharpness": tech_weights.sharpness * cat_weights.technical,
            "exposure_balance": tech_weights.exposure_balance * cat_weights.technical,
            "noise_level": tech_weights.noise_level * cat_weights.technical,
        }

        if not effective:
            return None

        return max(effective, key=effective.get)
