---
description: Photo scoring pipeline, multi-model consensus, weighted score computation
globs:
  - "photo_score/scoring/**/*.py"
  - "calibrate.py"
alwaysApply: false
---

# Scoring Pipeline

## Overview

Use this skill when working with the 7-step scoring pipeline, score computation, or multi-model consensus.

## Pipeline Steps (7 API calls)

```
1. Feature Extraction (Pixtral 12B)
   └─> scene_type, subject_position, lighting, background, etc.

2-3. Aesthetic Scoring (Qwen 50% + Gemini 50%)
   └─> composition, subject_strength, visual_appeal (0-1 each)

4-5. Technical Scoring (Qwen 50% + Gemini 50%)
   └─> sharpness, exposure, noise_level (0-1 each)

6. Metadata Extraction (Pixtral 12B)
   └─> description, location_name, location_country

7. Critique Generation (Gemini 3 Flash)
   └─> summary, strengths, improvements, key_recommendation
```

## Score Computation

```python
# Category scores (0-1)
aesthetic_score = (composition * 0.4) + (subject_strength * 0.35) + (visual_appeal * 0.25)
technical_score = (sharpness * 0.4) + (exposure * 0.35) + (noise_level * 0.25)

# Final score (0-100)
final_score = (aesthetic_score * 0.6 + technical_score * 0.4) * 100
```

## Score Tiers

| Score | Tier | Description |
|-------|------|-------------|
| 85-100 | Excellent | Portfolio-worthy |
| 70-84 | Strong | Well-executed |
| 50-69 | Competent | Solid snapshot |
| 30-49 | Tourist | Below average |
| 0-29 | Flawed | Technical issues |

## Multi-Model Consensus

```python
# Weighted average from multiple models
scores = [(model_score, weight) for model, weight in scorers]
final = sum(score * weight for score, weight in scores) / sum(weights)
```

## Resources

- [composite.py](photo_score/scoring/composite.py) - Main scoring engine
- [reducer.py](photo_score/scoring/reducer.py) - Score computation
- [README.md](README.md) - Architecture documentation
