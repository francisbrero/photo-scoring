"""Score calibration for local inference models.

Qwen2-VL-2B scores differently from Claude 3.5 Sonnet. This module
applies per-attribute affine transforms to align local scores closer
to the cloud baseline.
"""

from dataclasses import dataclass

from photo_score.storage.models import NormalizedAttributes


@dataclass
class CalibrationMap:
    """Per-attribute affine mapping: calibrated = clamp(slope * raw + intercept, 0, 1)."""

    composition: tuple[float, float]
    subject_strength: tuple[float, float]
    visual_appeal: tuple[float, float]
    sharpness: tuple[float, float]
    exposure_balance: tuple[float, float]
    noise_level: tuple[float, float]


# Initial conservative calibration.
# Qwen2-VL-2B is generally less critical than Claude 3.5 Sonnet.
# These scale down slightly. Will be refined with real comparison data.
DEFAULT_CALIBRATION = CalibrationMap(
    composition=(0.85, 0.0),
    subject_strength=(0.85, 0.0),
    visual_appeal=(0.80, 0.0),
    sharpness=(0.90, 0.0),
    exposure_balance=(0.90, 0.0),
    noise_level=(0.95, 0.0),
)


def _clamp(value: float) -> float:
    """Clamp value to [0, 1]."""
    return max(0.0, min(1.0, value))


def apply_calibration(
    attrs: NormalizedAttributes,
    cal: CalibrationMap,
) -> NormalizedAttributes:
    """Apply per-attribute affine transform, clamp to [0, 1].

    Returns a new NormalizedAttributes with calibrated values.
    """
    return NormalizedAttributes(
        image_id=attrs.image_id,
        composition=_clamp(cal.composition[0] * attrs.composition + cal.composition[1]),
        subject_strength=_clamp(
            cal.subject_strength[0] * attrs.subject_strength + cal.subject_strength[1]
        ),
        visual_appeal=_clamp(
            cal.visual_appeal[0] * attrs.visual_appeal + cal.visual_appeal[1]
        ),
        sharpness=_clamp(cal.sharpness[0] * attrs.sharpness + cal.sharpness[1]),
        exposure_balance=_clamp(
            cal.exposure_balance[0] * attrs.exposure_balance + cal.exposure_balance[1]
        ),
        noise_level=_clamp(cal.noise_level[0] * attrs.noise_level + cal.noise_level[1]),
        model_name=attrs.model_name,
        model_version=attrs.model_version,
        scored_at=attrs.scored_at,
    )
