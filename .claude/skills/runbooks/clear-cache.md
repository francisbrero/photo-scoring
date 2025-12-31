---
description: Step-by-step guide to clear or inspect the inference cache
globs:
  - "photo_score/storage/cache.py"
alwaysApply: false
---

# Runbook: Clear Cache

## Cache Location

```
~/.photo_score/cache.db
```

## Clear Entire Cache

```bash
rm ~/.photo_score/cache.db
```

Next run will re-create the database and re-infer all images.

## Inspect Cache

### View Cache Size
```bash
ls -lh ~/.photo_score/cache.db
```

### Count Cached Images
```bash
sqlite3 ~/.photo_score/cache.db "SELECT COUNT(DISTINCT image_id) FROM inference_results;"
```

### View Recent Entries
```bash
sqlite3 ~/.photo_score/cache.db "SELECT image_id, model_name, created_at FROM inference_results ORDER BY created_at DESC LIMIT 10;"
```

### Check Cache for Specific Image
```bash
# First get the image_id (SHA256 of file)
python -c "
import hashlib
with open('path/to/image.jpg', 'rb') as f:
    print(hashlib.sha256(f.read()).hexdigest())
"

# Then query
sqlite3 ~/.photo_score/cache.db "SELECT * FROM inference_results WHERE image_id = 'your-hash-here';"
```

## Clear Specific Model Results

```bash
sqlite3 ~/.photo_score/cache.db "DELETE FROM inference_results WHERE model_name = 'openai/gpt-4o-mini';"
```

## Clear Old Entries

```bash
# Clear entries older than 7 days
sqlite3 ~/.photo_score/cache.db "DELETE FROM inference_results WHERE created_at < datetime('now', '-7 days');"
```

## When to Clear Cache

- After modifying prompts
- After updating model configuration
- When scores seem stale or incorrect
- To force re-scoring with new models
- Before benchmarking (ensure fresh results)

## Cache Schema

```sql
-- Inference results table
CREATE TABLE inference_results (
    image_id TEXT,
    model_name TEXT,
    model_version TEXT,
    raw_response TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY (image_id, model_name, model_version)
);
```
