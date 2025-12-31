---
description: OpenRouter API client for vision model inference, image encoding, retry logic
globs:
  - "photo_score/inference/**/*.py"
  - "photo_score/scoring/composite.py"
alwaysApply: false
---

# OpenRouter Vision Client

## Overview

Use this skill when working with the OpenRouter API client, vision model inference, or image processing pipeline.

## Key Patterns

### API Client Structure
```python
from photo_score.inference.client import OpenRouterClient

with OpenRouterClient() as client:
    result = client._call_api(image_path, prompt, model=MODEL_NAME, max_tokens=256)
```

### Image Encoding
- Max dimension: 2048px (resized with LANCZOS)
- EXIF orientation applied via `ImageOps.exif_transpose()`
- Output format: JPEG base64, quality=85

### Model Configuration (in composite.py)
```python
MODELS = {
    "feature_extraction": "mistralai/pixtral-12b",
    "aesthetic_scorers": [("qwen/qwen2.5-vl-72b-instruct", 0.50), ("google/gemini-2.5-flash", 0.50)],
    "technical_scorers": [("qwen/qwen2.5-vl-72b-instruct", 0.50), ("google/gemini-2.5-flash", 0.50)],
    "metadata": "mistralai/pixtral-12b",
    "critique": "google/gemini-3-flash-preview",
}
```

### Retry Logic
- Max retries: 5
- Exponential backoff: 2^(attempt+1) seconds
- Handles: 429 rate limits, timeouts, connection errors

### JSON Extraction
Uses balanced brace matching to extract JSON from markdown code blocks or raw responses.

## Resources

- [OpenRouter API Docs](https://openrouter.ai/docs)
- [client.py](photo_score/inference/client.py)
- [composite.py](photo_score/scoring/composite.py)
