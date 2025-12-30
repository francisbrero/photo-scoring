# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal Photo Scoring CLI - a command-line tool that recursively analyzes photo collections using vision models (Claude 3.5 Sonnet via OpenRouter) and produces CSV rankings with diagnostic explanations. Optimizes for reproducibility, debuggability, and fast iteration on aesthetic preferences.

**Core principle**: Inference once, score many times. Vision model inference is cached in `~/.photo_score/cache.db`; scoring/explanation logic runs instantly from cached attributes.

## Build and Development Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run single test file
pytest tests/test_reducer.py

# Run with coverage
pytest --cov=photo_score

# Run the CLI
photo-score run --input ./photos --config ./configs/default.yaml --output ./scores.csv

# Re-score with different weights (no inference, uses cache)
photo-score rescore --input ./photos --config ./configs/custom.yaml --output ./scores.csv
```

## Environment Variables

- `OPENROUTER_API_KEY`: Required for vision model inference

## Project Structure

```
photo_score/
  cli.py                # Typer CLI entry point (run, rescore commands)
  ingestion/
    discover.py         # Recursive image discovery with SHA256 hashing
    metadata.py         # EXIF extraction
  inference/
    client.py           # OpenRouter API client
    prompts.py          # Vision model prompts for aesthetic/technical analysis
    schemas.py          # Pydantic response schemas
  scoring/
    reducer.py          # Weighted score computation with thresholds
    explanations.py     # Deterministic template-based explanations
  storage/
    cache.py            # SQLite cache (~/.photo_score/cache.db)
    models.py           # Pydantic data models
  config/
    loader.py           # YAML config loading
    schema.py           # Config validation schemas
  output/
    csv_writer.py       # CSV output generation
tests/                  # pytest test suite
configs/default.yaml    # Default scoring configuration
```

## Architecture Notes

1. **Attributes**: All normalized to [0, 1] range
   - Aesthetic: composition, subject_strength, visual_appeal
   - Technical: sharpness, exposure_balance, noise_level

2. **Scoring reducer** (`scoring/reducer.py`): Weighted sum with hard thresholds. Exposes per-attribute contributions for explanations.

3. **Explanations** (`scoring/explanations.py`): Template-driven, deterministic, weight-aware. No LLM calls.

4. **Caching** (`storage/cache.py`): SQLite at `~/.photo_score/cache.db`. Stores image_id (SHA256), raw model outputs, normalized attributes.

5. **Two-pass inference**: Aesthetic prompt and technical prompt run separately against OpenRouter, results merged into NormalizedAttributes.

## CLI Usage

```bash
# Full run (discovery + inference + scoring + CSV output)
photo-score run \
  --input ./photos/japan \
  --config ./configs/default.yaml \
  --output ./outputs/japan_scores.csv

# Re-score from cache (instant, no API calls)
photo-score rescore \
  --input ./photos/japan \
  --config ./configs/high_sharpness.yaml \
  --output ./outputs/japan_rescored.csv
```
