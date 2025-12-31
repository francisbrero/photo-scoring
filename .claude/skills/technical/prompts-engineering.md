---
description: Vision model prompts for photo analysis, aesthetic and technical scoring
globs:
  - "photo_score/inference/prompts*.py"
alwaysApply: false
---

# Prompt Engineering

## Overview

Use this skill when modifying prompts for feature extraction, scoring, metadata, or critique generation.

## Prompt Files

- `prompts.py` - Legacy single-model prompts
- `prompts_v2.py` - Current multi-model prompts with calibration guidance

## Prompt Structure

### Feature Extraction Prompt
Extracts structured metadata about scene, lighting, composition:
```json
{
  "scene_type": "landscape|portrait|street|architecture|nature|food|event|other",
  "main_subject": "brief description",
  "subject_position": "center|rule_of_thirds|off_center|multiple",
  "background": "clean|busy|blurred|contextual",
  "lighting": "natural_soft|natural_harsh|golden_hour|blue_hour|artificial|mixed|low_light",
  "color_palette": "vibrant|muted|monochrome|warm|cool|neutral",
  "depth_of_field": "shallow|medium|deep",
  "technical_issues": ["blur", "noise", "overexposed", "underexposed", "tilted", "none"]
}
```

### Scoring Prompts (Aesthetic & Technical)
Include calibration guidance for consistent scoring:
```
Calibration:
- 0.8-1.0: Exceptional, portfolio-worthy
- 0.6-0.7: Strong, intentional photography
- 0.4-0.5: Average, "camera did its job"
- 0.2-0.3: Below average, tourist snapshot
- 0.0-0.1: Poor, no aesthetic merit
```

### Critique Prompt
Receives all context (features, scores) and generates educational feedback:
```json
{
  "summary": "2-3 sentences overall assessment",
  "working_well": ["specific strength with WHY"],
  "could_improve": ["specific issue with concrete suggestion"],
  "key_recommendation": "single most impactful change"
}
```

## Best Practices

1. **Enforce JSON output** - Always specify exact JSON schema expected
2. **Provide calibration** - Give examples of what each score range means
3. **Be specific** - "composition" is vague, specify what aspects to evaluate
4. **Include reasoning** - Ask for brief reasoning to improve quality

## Resources

- [prompts_v2.py](photo_score/inference/prompts_v2.py) - Current prompts
- [schemas.py](photo_score/inference/schemas.py) - Pydantic response schemas
