---
description: Start the web viewer to review scored photos
argument-hint: <photos-dir> [results.csv]
allowed-tools: Bash(uv run python:*)
---

# Start Web Viewer

Launch the Flask web viewer to review scored photos with critiques.

## Usage

```
/viewer /path/to/photos
/viewer /path/to/photos results.csv
```

## Steps

1. Find the CSV file (default: results.csv)
2. Start serve_viewer.py in background
3. Open http://localhost:8080

## Command

```bash
uv run python serve_viewer.py --photos $1 --csv ${2:-results.csv} --port 8080
```

Run in background so user can continue working.
