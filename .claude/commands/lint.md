---
description: Check code style with ruff (linting and formatting)
allowed-tools: Bash(uv run ruff:*)
---

# Lint Code

Check code style and formatting with ruff.

## Usage

```
/lint
```

## What It Checks

- Code style violations (ruff check)
- Formatting issues (ruff format --check)

## Command

```bash
uv run ruff check . && uv run ruff format --check .
```

## Auto-Fix

To automatically fix issues, use `/fix` instead.
