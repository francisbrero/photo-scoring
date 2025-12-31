---
description: SQLite caching layer for inference results, cache management
globs:
  - "photo_score/storage/**/*.py"
alwaysApply: false
---

# SQLite Cache Layer

## Overview

Use this skill when working with the caching system that stores inference results to avoid redundant API calls.

## Cache Location

```
~/.photo_score/cache.db
```

## Schema

```sql
-- Raw inference results from models
CREATE TABLE inference_results (
    image_id TEXT,           -- SHA256 hash of image content
    model_name TEXT,
    model_version TEXT,
    raw_response TEXT,       -- JSON string
    created_at TIMESTAMP,
    PRIMARY KEY (image_id, model_name, model_version)
);

-- Normalized attribute scores
CREATE TABLE normalized_attributes (
    image_id TEXT PRIMARY KEY,
    composition REAL,
    subject_strength REAL,
    visual_appeal REAL,
    sharpness REAL,
    exposure_balance REAL,
    noise_level REAL,
    model_name TEXT,
    model_version TEXT,
    created_at TIMESTAMP
);
```

## Cache API

```python
from photo_score.storage.cache import Cache

cache = Cache()

# Check for existing inference
result = cache.get_inference(image_id, model_version)

# Store new inference
cache.store_inference(image_id, model_name, model_version, raw_response)

# Get/store normalized attributes
attrs = cache.get_attributes(image_id)
cache.store_attributes(image_id, attributes)
```

## Image ID Generation

```python
import hashlib
from pathlib import Path

def generate_image_id(path: Path) -> str:
    """SHA256 hash of file contents."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()
```

## Cache Invalidation

- Cache is keyed by `(image_id, model_version)`
- Changing model version triggers re-inference
- Manually clear: `rm ~/.photo_score/cache.db`

## Resources

- [cache.py](photo_score/storage/cache.py) - Cache implementation
- [models.py](photo_score/storage/models.py) - Data models
