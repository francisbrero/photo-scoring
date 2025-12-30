"""Scoring reducer for computing final scores from attributes."""

from photo_score.config.schema import ScoringConfig
from photo_score.storage.models import NormalizedAttributes, ScoringResult


class ScoringReducer:
    """Computes aggregate scores from normalized attributes."""

    def __init__(self, config: ScoringConfig):
        """Initialize reducer with scoring configuration."""
        self.config = config

    def compute_scores(
        self, image_id: str, image_path: str, attributes: NormalizedAttributes
    ) -> ScoringResult:
        """Compute all scores for an image.

        Args:
            image_id: Unique identifier for the image.
            image_path: Path to the image (for output).
            attributes: Normalized attribute values.

        Returns:
            ScoringResult with all computed scores and contributions.
        """
        # Compute category scores
        aesthetic_score = self._compute_aesthetic_score(attributes)
        technical_score = self._compute_technical_score(attributes)

        # Compute final score (0-100 scale)
        cat_weights = self.config.category_weights
        raw_final = (
            aesthetic_score * cat_weights.aesthetic
            + technical_score * cat_weights.technical
        )

        # Apply threshold penalties
        final_score = self._apply_thresholds(raw_final, attributes)

        # Compute per-attribute contributions
        contributions = self._compute_contributions(attributes)

        return ScoringResult(
            image_id=image_id,
            image_path=image_path,
            final_score=round(final_score * 100, 2),
            technical_score=round(technical_score, 4),
            aesthetic_score=round(aesthetic_score, 4),
            attributes=attributes,
            contributions=contributions,
        )

    def _compute_aesthetic_score(self, attrs: NormalizedAttributes) -> float:
        """Compute weighted aesthetic score (0-1)."""
        weights = self.config.weights.aesthetic
        total_weight = weights.composition + weights.subject_strength + weights.visual_appeal

        score = (
            attrs.composition * weights.composition
            + attrs.subject_strength * weights.subject_strength
            + attrs.visual_appeal * weights.visual_appeal
        ) / total_weight

        return score

    def _compute_technical_score(self, attrs: NormalizedAttributes) -> float:
        """Compute weighted technical score (0-1)."""
        weights = self.config.weights.technical
        total_weight = weights.sharpness + weights.exposure_balance + weights.noise_level

        score = (
            attrs.sharpness * weights.sharpness
            + attrs.exposure_balance * weights.exposure_balance
            + attrs.noise_level * weights.noise_level
        ) / total_weight

        return score

    def _apply_thresholds(
        self, score: float, attrs: NormalizedAttributes
    ) -> float:
        """Apply hard threshold penalties."""
        thresholds = self.config.thresholds

        # Cap score if below sharpness threshold
        if attrs.sharpness < thresholds.sharpness_min:
            penalty = (thresholds.sharpness_min - attrs.sharpness) / thresholds.sharpness_min
            score = score * (1 - penalty * 0.5)  # Up to 50% penalty

        # Cap score if below exposure threshold
        if attrs.exposure_balance < thresholds.exposure_min:
            penalty = (thresholds.exposure_min - attrs.exposure_balance) / thresholds.exposure_min
            score = score * (1 - penalty * 0.3)  # Up to 30% penalty

        return max(0.0, min(1.0, score))

    def _compute_contributions(
        self, attrs: NormalizedAttributes
    ) -> dict[str, float]:
        """Compute per-attribute contribution to final score.

        Returns:
            Dictionary mapping attribute name to its contribution value.
            Contributions are the weighted value that each attribute adds.
        """
        aes_weights = self.config.weights.aesthetic
        tech_weights = self.config.weights.technical
        cat_weights = self.config.category_weights

        # Normalize within categories
        aes_total = aes_weights.composition + aes_weights.subject_strength + aes_weights.visual_appeal
        tech_total = tech_weights.sharpness + tech_weights.exposure_balance + tech_weights.noise_level

        contributions = {}

        # Aesthetic contributions
        contributions["composition"] = (
            attrs.composition
            * (aes_weights.composition / aes_total)
            * cat_weights.aesthetic
        )
        contributions["subject_strength"] = (
            attrs.subject_strength
            * (aes_weights.subject_strength / aes_total)
            * cat_weights.aesthetic
        )
        contributions["visual_appeal"] = (
            attrs.visual_appeal
            * (aes_weights.visual_appeal / aes_total)
            * cat_weights.aesthetic
        )

        # Technical contributions
        contributions["sharpness"] = (
            attrs.sharpness
            * (tech_weights.sharpness / tech_total)
            * cat_weights.technical
        )
        contributions["exposure_balance"] = (
            attrs.exposure_balance
            * (tech_weights.exposure_balance / tech_total)
            * cat_weights.technical
        )
        contributions["noise_level"] = (
            attrs.noise_level
            * (tech_weights.noise_level / tech_total)
            * cat_weights.technical
        )

        # Round for readability
        return {k: round(v, 4) for k, v in contributions.items()}
