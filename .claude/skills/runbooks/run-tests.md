---
description: Step-by-step guide to run the test suite for both CLI and cloud packages
globs:
  - "tests/**/*.py"
  - "packages/api/tests/**/*.py"
alwaysApply: false
---

# Runbook: Run Tests

## Quick Reference

| Package | Command | Requirements |
|---------|---------|--------------|
| CLI (photo_score) | `uv run pytest -v` | None |
| Cloud (packages/api) | `uv run pytest tests/ -v` | Local Supabase |

---

## CLI Package Tests

```bash
cd /Users/francis/Documents/MadKudu/photo-scoring
uv run pytest -v
```

### With Coverage

```bash
uv run pytest --cov=photo_score --cov-report=term-missing -v
```

---

## Cloud Package Tests

### Prerequisites

1. **Start local Supabase** (required for integration tests):
   ```bash
   supabase start
   supabase status  # Verify it's running
   ```

2. **Navigate to cloud package**:
   ```bash
   cd /Users/francis/Documents/MadKudu/photo-scoring/packages/api
   ```

### Run All Tests

```bash
uv run pytest tests/ -v
```

### Run Unit Tests Only (No Supabase)

```bash
uv run pytest tests/ -v \
  --ignore=tests/test_integration.py \
  --ignore=tests/test_e2e_user_journey.py
```

### Run Integration Tests Only

```bash
uv run pytest tests/test_integration.py -v
```

### Run E2E Tests Only

```bash
uv run pytest tests/test_e2e_user_journey.py -v
```

### With Coverage

```bash
uv run pytest tests/ --cov=api --cov-report=term-missing
```

---

## Test Options

| Flag | Description |
|------|-------------|
| `-v` | Verbose output |
| `-x` | Stop on first failure |
| `--lf` | Run only last failed tests |
| `-k "pattern"` | Run tests matching pattern |
| `--tb=short` | Shorter traceback |
| `--cov=<module>` | Enable coverage |
| `--cov-report=html` | Generate HTML coverage report |

---

## Test Categories (Cloud)

| Category | File | Requires Supabase |
|----------|------|-------------------|
| Unit | `test_health.py`, `test_credits.py`, etc. | No |
| Integration | `test_integration.py` | Yes |
| E2E | `test_e2e_user_journey.py` | Yes |

---

## Troubleshooting

### "Supabase not running" skip message

```bash
supabase start
```

### Invalid JWT errors

Check credentials match local Supabase:
```bash
supabase status --output json | jq '.SERVICE_ROLE_KEY'
```

### Reset database

```bash
supabase db reset  # WARNING: Deletes all data
```

---

## Full Documentation

See `packages/api/TESTING.md` for:
- Writing new tests
- Fixture reference
- Cost considerations
- Mocking guidelines
