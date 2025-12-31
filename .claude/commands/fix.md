---
description: Auto-fix code style issues with ruff
allowed-tools: Bash(uv run ruff:*)
---

# Fix Code Style

Automatically fix code style and formatting issues with ruff.

## Usage

```
/fix
```

## What It Fixes

- Auto-fixable lint violations (ruff check --fix)
- Formatting issues (ruff format)

## Command

```bash
uv run ruff check --fix . && uv run ruff format .
```

## Note

Some issues cannot be auto-fixed and require manual intervention.
Run `/lint` after to verify all issues are resolved.
