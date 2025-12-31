---
description: Step-by-step guide to add a new vision model to the scoring pipeline
globs:
  - "photo_score/scoring/composite.py"
  - "photo_score/inference/client.py"
alwaysApply: false
---

# Runbook: Add New Model

## Overview

Add a new vision model to the multi-model scoring pipeline.

## Steps

### 1. Find Model on OpenRouter

Browse https://openrouter.ai/models and find a vision-capable model.

Note:
- Model ID (e.g., `anthropic/claude-3.5-sonnet`)
- Pricing (input/output per million tokens)
- Context window
- Vision support

### 2. Update Model Configuration

Edit `photo_score/scoring/composite.py`:

```python
MODELS = {
    "feature_extraction": "mistralai/pixtral-12b",
    "aesthetic_scorers": [
        ("qwen/qwen2.5-vl-72b-instruct", 0.40),
        ("google/gemini-2.5-flash", 0.40),
        ("new/model-id", 0.20),  # Add new model with weight
    ],
    # ... similar for technical_scorers
}
```

**Important**: Weights must sum to 1.0

### 3. Test the Model

```bash
# Test with a single image first
uv run python -c "
from photo_score.inference.client import OpenRouterClient
from pathlib import Path

client = OpenRouterClient()
result = client._call_api(
    Path('test_photos/sample.jpg'),
    'Describe this image in JSON format.',
    model='new/model-id'
)
print(result)
"
```

### 4. Check Response Format

Ensure the model returns valid JSON matching our schemas:

```python
# Expected aesthetic response
{
    "composition": 0.7,
    "subject_strength": 0.8,
    "visual_appeal": 0.65,
    "reasoning": "..."
}
```

### 5. Handle Model-Specific Issues

Some models may need adjustments in `client.py`:
- Different max_tokens limits
- JSON extraction quirks
- Rate limiting differences

### 6. Update Cost Estimates

Edit `README.md` and `CLAUDE.md` with new cost per image.

### 7. Test Full Pipeline

```bash
# Clear cache to force re-inference
rm ~/.photo_score/cache.db

# Run on test images
uv run python calibrate.py -i test_photos -o test_results.csv -n 5
```

### 8. Compare Results

Check if new model improves or degrades scores compared to baseline.

## Rollback

To remove a model, simply remove it from the `MODELS` dict and adjust weights.
