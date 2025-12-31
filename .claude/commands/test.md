---
description: Run the test suite with coverage reporting
argument-hint: [test-file] [-k pattern] [--lf]
allowed-tools: Bash(uv run pytest:*)
---

# Run Tests

Execute the pytest test suite with coverage analysis.

## Usage

```
/test
/test tests/test_reducer.py
/test -k "cache"
/test --lf
```

## Options

- No args: Run all tests with coverage
- `<file>`: Run specific test file
- `-k <pattern>`: Run tests matching pattern
- `--lf`: Run only last failed tests
- `-x`: Stop on first failure

## Command

```bash
uv run pytest --cov=photo_score --cov-report=term-missing -v $ARGUMENTS
```

## Test Files

- `tests/test_cache.py` - SQLite cache tests
- `tests/test_config.py` - Configuration tests
- `tests/test_explanations.py` - Explanation generation
- `tests/test_reducer.py` - Score computation
