# Run Tests

Run the test suite with coverage reporting.

## Usage
```
/run-tests [options]
```

## Instructions

When the user invokes this skill:

1. **Run pytest with coverage**
   ```bash
   cd /Users/francis/Documents/MadKudu/photo-scoring
   uv run pytest --cov=photo_score --cov-report=term-missing -v
   ```

2. **Report results**
   - Show test pass/fail summary
   - Highlight any failures with details
   - Show coverage percentage

3. **If tests fail**
   - Offer to investigate and fix the failing tests
   - Show the specific error messages

## Options
- `-v` - Verbose output (default)
- `-x` - Stop on first failure
- `--lf` - Run only last failed tests
- `-k [pattern]` - Run tests matching pattern

## Examples
```
/run-tests
/run-tests -k "test_reducer"
/run-tests --lf
```
