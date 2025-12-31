---
description: Score photos in a directory using the multi-model scoring pipeline
argument-hint: <directory> [output.csv] [--limit N]
allowed-tools: Bash(uv run python:*)
---

# Score Photos

Score photos using the multi-model vision pipeline (Qwen + Gemini).

## Usage

```
/score /path/to/photos
/score /path/to/photos results.csv
/score /path/to/photos results.csv --limit 10
```

## Steps

1. Verify OPENROUTER_API_KEY is set
2. Run calibrate.py with the specified directory
3. Report summary of results
4. Offer to start the web viewer

## Cost

~$0.005 per image (7 API calls)

## Command

```bash
uv run python calibrate.py -i $ARGUMENTS
```
