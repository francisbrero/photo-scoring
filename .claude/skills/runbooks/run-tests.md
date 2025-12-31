---
description: Step-by-step guide to run the test suite
globs:
  - "tests/**/*.py"
alwaysApply: false
---

# Runbook: Run Tests

## Quick Run

```bash
cd /Users/francis/Documents/MadKudu/photo-scoring
uv run pytest -v
```

## With Coverage

```bash
uv run pytest --cov=photo_score --cov-report=term-missing -v
```

## Run Specific Tests

```bash
# Single file
uv run pytest tests/test_reducer.py -v

# Single test function
uv run pytest tests/test_reducer.py::test_weighted_sum -v

# Pattern matching
uv run pytest -k "test_cache" -v
```

## Test Options

| Flag | Description |
|------|-------------|
| `-v` | Verbose output |
| `-x` | Stop on first failure |
| `--lf` | Run only last failed tests |
| `-k "pattern"` | Run tests matching pattern |
| `--cov=photo_score` | Enable coverage |
| `--cov-report=html` | Generate HTML coverage report |

## Test Structure

```
tests/
├── test_cache.py        # SQLite cache tests
├── test_config.py       # Configuration loading tests
├── test_explanations.py # Explanation generation tests
└── test_reducer.py      # Score computation tests
```

## Writing New Tests

```python
# tests/test_example.py
import pytest
from photo_score.scoring.reducer import ScoringReducer

def test_example():
    """Test description."""
    reducer = ScoringReducer(config)
    result = reducer.compute_scores(attributes)
    assert result.final_score > 0
```

## CI Integration

Tests run automatically on:
- Pull request creation
- Push to master/main

See `.github/workflows/test.yml`
