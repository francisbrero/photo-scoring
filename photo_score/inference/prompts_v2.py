"""Vision model prompts for multi-model scoring system.

This module contains prompts optimized for different models:
- FEATURE_EXTRACTION: Rich feature extraction using Pixtral (cheap, detailed)
- SCORING prompts: Calibrated scoring prompts for different models
"""

# =============================================================================
# FEATURE EXTRACTION (Pixtral - cheap, fast, detailed)
# =============================================================================

FEATURE_EXTRACTION_PROMPT = """Analyze this photograph and extract detailed features. Be objective and thorough.

Respond with ONLY a JSON object:
{
  "scene_type": "<landscape|portrait|street|architecture|nature|food|event|other>",
  "main_subject": "<brief description of the main subject>",
  "subject_position": "<center|rule_of_thirds|off_center|multiple>",
  "background": "<clean|busy|blurred|contextual>",
  "lighting": "<natural_soft|natural_harsh|golden_hour|blue_hour|artificial|mixed|low_light>",
  "color_palette": "<vibrant|muted|monochrome|warm|cool|neutral>",
  "depth_of_field": "<shallow|medium|deep>",
  "motion": "<static|implied|blur|frozen>",
  "human_presence": "<none|main_subject|secondary|crowd>",
  "text_or_signs": <true|false>,
  "weather_visible": "<clear|cloudy|rain|fog|none>",
  "time_of_day": "<dawn|morning|midday|afternoon|golden_hour|dusk|night|unknown>",
  "technical_issues": ["<list any: blur, noise, overexposed, underexposed, tilted, none>"],
  "notable_elements": ["<list 2-3 notable visual elements>"],
  "estimated_location_type": "<urban|rural|coastal|mountain|indoor|tourist_site|unknown>"
}

Be factual. Report what you observe, not interpretations."""

# =============================================================================
# AESTHETIC SCORING (calibrated for each model)
# =============================================================================

# Generic harsh scoring prompt (works for most models)
AESTHETIC_SCORING_PROMPT = """Rate this photograph's aesthetic quality. Be harsh - most casual photos are mediocre.

CALIBRATION:
- 0.8-1.0: Exceptional, portfolio-worthy
- 0.6-0.7: Strong, intentional photography
- 0.4-0.5: Average, "camera did its job"
- 0.2-0.3: Below average, tourist snapshot
- 0.0-0.1: Poor, no aesthetic merit

Respond with ONLY a JSON object:
{
  "composition": <float 0.0-1.0>,
  "subject_strength": <float 0.0-1.0>,
  "visual_appeal": <float 0.0-1.0>,
  "reasoning": "<one sentence explaining the scores>"
}

Most travel photos should score 0.3-0.5. Be critical."""

# =============================================================================
# TECHNICAL SCORING
# =============================================================================

TECHNICAL_SCORING_PROMPT = """Rate this photograph's technical execution. Focus on camera work, not aesthetics.

CALIBRATION:
- 0.8-1.0: Professional quality, no flaws
- 0.6-0.7: Good execution, minor issues
- 0.4-0.5: Acceptable, typical auto-mode results
- 0.2-0.3: Technical problems present
- 0.0-0.1: Severely flawed

Respond with ONLY a JSON object:
{
  "sharpness": <float 0.0-1.0>,
  "exposure": <float 0.0-1.0>,
  "noise_level": <float 0.0-1.0>,
  "reasoning": "<one sentence explaining the scores>"
}

Note: noise_level is inverted (1.0 = clean, no noise)."""

# =============================================================================
# METADATA (description + location)
# =============================================================================

METADATA_PROMPT = """Describe this photograph briefly and identify the location if possible.

Respond with ONLY a JSON object:
{
  "description": "<1-2 sentence description>",
  "location_name": "<specific place name or null>",
  "location_country": "<country or null>"
}

Be concise. Use null if location cannot be determined."""
