---
description: Clear the inference cache to force re-scoring
allowed-tools: Bash(rm:*)
---

# Clear Cache

Remove the SQLite cache to force re-inference on next scoring run.

## Usage

```
/clear-cache
```

## Cache Location

```
~/.photo_score/cache.db
```

## Command

```bash
rm -f ~/.photo_score/cache.db && echo "Cache cleared successfully"
```

## When to Clear

- After modifying prompts
- After changing model configuration
- When scores seem incorrect
- Before benchmarking (ensure fresh results)

## Warning

This will require re-running all API calls on next score, which incurs costs.
