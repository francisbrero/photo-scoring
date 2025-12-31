---
description: Step-by-step guide to modify scoring prompts
globs:
  - "photo_score/inference/prompts*.py"
alwaysApply: false
---

# Runbook: Modify Prompts

## Overview

Modify the prompts used for feature extraction, scoring, or critique generation.

## Prompt Files

```
photo_score/inference/
├── prompts.py      # Legacy (single model)
└── prompts_v2.py   # Current (multi-model with calibration)
```

## Steps

### 1. Identify Which Prompt to Modify

| Task | Prompt Variable | File |
|------|-----------------|------|
| Feature extraction | `FEATURE_EXTRACTION_PROMPT` | prompts_v2.py |
| Aesthetic scoring | `AESTHETIC_PROMPT_V2` | prompts_v2.py |
| Technical scoring | `TECHNICAL_PROMPT_V2` | prompts_v2.py |
| Metadata | `METADATA_PROMPT` | prompts.py |
| Critique | `CRITIQUE_PROMPT` | prompts_v2.py |

### 2. Edit the Prompt

```python
# prompts_v2.py
AESTHETIC_PROMPT_V2 = """
You are an expert photography critic...

[Your modifications here]

Return JSON:
{
  "composition": 0.0-1.0,
  "subject_strength": 0.0-1.0,
  "visual_appeal": 0.0-1.0,
  "reasoning": "one sentence"
}
"""
```

### 3. Update Response Schema (if needed)

If changing JSON structure, update `photo_score/inference/schemas.py`:

```python
class AestheticResponse(BaseModel):
    composition: float = Field(ge=0, le=1)
    subject_strength: float = Field(ge=0, le=1)
    visual_appeal: float = Field(ge=0, le=1)
    reasoning: str
    # Add new fields here
```

### 4. Clear Cache

```bash
rm ~/.photo_score/cache.db
```

### 5. Test with Single Image

```bash
uv run python -c "
from photo_score.inference.client import OpenRouterClient
from pathlib import Path

client = OpenRouterClient()
result = client.analyze_aesthetic(Path('test_photos/sample.jpg'))
print(result)
"
```

### 6. Run Full Test

```bash
uv run python calibrate.py -i test_photos -o test_results.csv -n 3
```

### 7. Compare Results

Check if prompt changes improve scoring quality or critique helpfulness.

## Best Practices

1. **Keep JSON schema stable** - Changing structure requires schema updates
2. **Include calibration** - Guide models on what scores mean
3. **Be specific** - Vague criteria lead to inconsistent scores
4. **Test incrementally** - Small changes, verify, repeat
