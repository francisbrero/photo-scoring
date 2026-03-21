# AGENTS.md

Universal context for AI coding agents working in this repository.

## Project Overview

Photo Scoring is a monorepo for analyzing photo collections using vision models (Qwen, Gemini via OpenRouter). It scores images on aesthetic and technical quality and produces ranked output with AI-generated critiques.

**Core principle**: Inference once, score many times. Vision model inference is cached; scoring/explanation logic runs instantly from cached attributes.

**Cost**: ~$0.005 per image (7 API calls).

## Repository Structure

This is a monorepo with four components:

```
/                          # Root Python package (CLI tool)
  photo_score/             # Core scoring library
  tests/                   # pytest test suite
  configs/                 # YAML scoring configs
  calibrate.py             # Main calibration script
  serve_viewer.py          # Local web viewer server

packages/
  api/                     # Cloud backend (FastAPI + Supabase)
  webapp/                  # Web frontend (React + Vite + Tailwind)
  desktop/                 # Electron desktop app with Python sidecar

supabase/
  migrations/              # Database migrations
  functions/               # Edge functions
```

## Tech Stack

| Component | Language | Framework | Package Manager |
|-----------|----------|-----------|-----------------|
| Core CLI | Python 3.11 | Typer, Pydantic, httpx | uv |
| API | Python 3.11+ | FastAPI, Supabase SDK | uv |
| Webapp | TypeScript | React 19, Vite, Tailwind 4 | npm |
| Desktop | TypeScript | Electron, React, Vite | npm |
| Desktop Sidecar | Python 3.11 | FastAPI, PyInstaller | uv |

## Setup

### Root CLI package

```bash
uv sync --dev
export OPENROUTER_API_KEY="your-key"
```

### API package

```bash
cd packages/api
uv sync --dev
# Requires .env with Supabase and OpenRouter credentials
```

### Webapp

```bash
cd packages/webapp
npm install
npm run dev
```

### Desktop

```bash
cd packages/desktop
npm install
npm run dev
```

## Common Commands

### Root (CLI)

```bash
uv run pytest -v                                        # Run tests
uv run pytest --cov=photo_score --cov-report=term-missing  # Tests with coverage
uv run ruff check .                                     # Lint
uv run ruff format .                                    # Format
uv run ruff check --fix . && uv run ruff format .       # Auto-fix
uv run python calibrate.py -i ./photos -o results.csv   # Score photos
uv run python serve_viewer.py --photos ./photos --csv results.csv  # Web viewer
```

### API

```bash
cd packages/api
uv run ruff check . && uv run ruff format .             # Lint & format
uv run pytest                                           # Tests (async)
uv run uvicorn api.main:app --reload                    # Dev server
```

### Webapp

```bash
cd packages/webapp
npm run dev        # Dev server
npm run build      # Production build (tsc + vite)
npm run lint       # ESLint
```

### Desktop

```bash
cd packages/desktop
npm run dev        # Dev (Electron + Vite)
npm run build      # Build main + renderer
npm run dist:mac   # Package for macOS
```

## Environment Variables

- `OPENROUTER_API_KEY` - Required for vision model inference (root CLI and API)
- Supabase credentials in `packages/api/.env` for the cloud backend

## Architecture

### Core Scoring Pipeline

1. **Discovery** (`photo_score/ingestion/discover.py`) - Recursive image discovery with SHA256 hashing
2. **EXIF** (`photo_score/ingestion/metadata.py`) - Extract camera metadata
3. **Inference** (`photo_score/inference/`) - Two-pass: aesthetic prompt + technical prompt via OpenRouter
4. **Caching** (`photo_score/storage/cache.py`) - SQLite at `~/.photo_score/cache.db` keyed by SHA256
5. **Scoring** (`photo_score/scoring/reducer.py`) - Weighted sum with hard thresholds
6. **Explanations** (`photo_score/scoring/explanations.py`) - Template-driven, deterministic, no LLM calls
7. **Output** (`photo_score/output/csv_writer.py`) - Ranked CSV

### Attributes (all normalized to [0, 1])

- **Aesthetic**: composition, subject_strength, visual_appeal
- **Technical**: sharpness, exposure_balance, noise_level

### Cloud Architecture

- **API** (`packages/api/`) - FastAPI backend, handles uploads, triggers scoring, stores results in Supabase
- **Webapp** (`packages/webapp/`) - React SPA, Supabase Auth, displays scored photos
- **Desktop** (`packages/desktop/`) - Electron app bundling a Python sidecar for offline scoring

### Database

Supabase (PostgreSQL) with migrations in `supabase/migrations/`. Includes storage buckets for photo uploads and RLS policies.

## Code Style

- **Python**: Ruff for linting and formatting. Target Python 3.11. Use type hints. Pydantic for data models.
- **TypeScript**: ESLint. React 19 with functional components and hooks. Tailwind for styling.
- Prefer simple, focused changes. Avoid over-engineering.
- All attributes are [0, 1] floats. Weights are defined in YAML configs.

## Testing

- **Root**: `uv run pytest -v` (pytest, sync tests)
- **API**: `uv run pytest` in `packages/api/` (pytest-asyncio, async tests)
- **Desktop**: `npm run test:e2e` (Playwright)
- Always run tests after making changes to verify nothing is broken.

## Files to Never Commit

These are in `.gitignore`:

- `.env`, `.env.local` - Secrets
- `*.csv` - Generated results
- `*.db` - SQLite cache
- `*.jpg`, `*.jpeg`, `*.png`, `*.heic` (and uppercase variants) - Photo files
- `photo_corrections_*.json` - Viewer correction exports
- `test_photos/`, `calibration_photos/` - Test image directories
- `packages/desktop/sidecar-dist/` - Built sidecar binaries
- `packages/desktop/node_modules/`, `packages/desktop/release/` - Build artifacts
