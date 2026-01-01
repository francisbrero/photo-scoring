---
description: Run the test suite with coverage reporting (project)
argument-hint: [cloud|cli|all] [test-file] [-k pattern] [--lf]
allowed-tools: Bash(uv run pytest:*), Bash(supabase:*)
---

# Run Tests

Execute the pytest test suite with coverage analysis.

## Usage

```
/test                           # Run CLI tests (from repo root)
/test cloud                     # Run cloud backend tests
/test cloud integration         # Run cloud integration tests only
/test cloud unit                # Run cloud unit tests only
/test -k "cache"                # Run tests matching pattern
/test --lf                      # Run only last failed tests
```

## Behavior

Based on arguments:

1. **No args or `cli`**: Run CLI package tests from repo root
2. **`cloud`**: Run all cloud tests (requires local Supabase for integration)
3. **`cloud unit`**: Run cloud unit tests only (no Supabase needed)
4. **`cloud integration`**: Run cloud integration tests only
5. **`cloud e2e`**: Run cloud e2e tests only

## Prerequisites for Cloud Tests

Integration and e2e tests require local Supabase:
```bash
supabase start
supabase status  # Verify running
```

## Commands

### CLI Tests (default)
```bash
cd /Users/francis/Documents/MadKudu/photo-scoring
uv run pytest --cov=photo_score --cov-report=term-missing -v $ARGUMENTS
```

### Cloud Tests (all)
```bash
cd /Users/francis/Documents/MadKudu/photo-scoring/packages/cloud
uv run pytest tests/ --cov=api --cov-report=term-missing -v
```

### Cloud Unit Tests (no Supabase)
```bash
cd /Users/francis/Documents/MadKudu/photo-scoring/packages/cloud
uv run pytest tests/ -v --ignore=tests/test_integration.py --ignore=tests/test_e2e_user_journey.py
```

### Cloud Integration Tests
```bash
cd /Users/francis/Documents/MadKudu/photo-scoring/packages/cloud
uv run pytest tests/test_integration.py -v
```

### Cloud E2E Tests
```bash
cd /Users/francis/Documents/MadKudu/photo-scoring/packages/cloud
uv run pytest tests/test_e2e_user_journey.py -v
```

## Test Categories

| Package | Category | Files | Supabase |
|---------|----------|-------|----------|
| CLI | Unit | `tests/test_*.py` | No |
| Cloud | Unit | `test_health.py`, `test_credits.py`, etc. | No |
| Cloud | Integration | `test_integration.py` | Yes |
| Cloud | E2E | `test_e2e_user_journey.py` | Yes |

## Important Notes

- **Cloud integration tests automatically skip** if Supabase is not running
- **Never call OpenRouter in tests** - always mock AI services
- See `packages/cloud/TESTING.md` for full testing documentation
