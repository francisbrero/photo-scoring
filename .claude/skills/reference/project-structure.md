---
description: Project structure reference, file organization
globs: []
alwaysApply: true
---

# Project Structure

## Directory Layout

```
photo-scoring/
├── calibrate.py              # Main CLI entry point for scoring
├── serve_viewer.py           # Flask web viewer server
├── pyproject.toml            # Project config and dependencies
├── CLAUDE.md                 # Claude Code guidance
├── README.md                 # User documentation
│
├── photo_score/              # Main package
│   ├── __init__.py
│   ├── cli.py                # Typer CLI (legacy)
│   │
│   ├── inference/            # Vision model interaction
│   │   ├── client.py         # OpenRouter API client
│   │   ├── prompts.py        # Legacy prompts
│   │   ├── prompts_v2.py     # Current multi-model prompts
│   │   └── schemas.py        # Pydantic response schemas
│   │
│   ├── scoring/              # Score computation
│   │   ├── composite.py      # Multi-model scoring engine ⭐
│   │   ├── reducer.py        # Weighted score computation
│   │   └── explanations.py   # Legacy explanation generation
│   │
│   ├── storage/              # Data persistence
│   │   ├── cache.py          # SQLite cache layer
│   │   └── models.py         # Pydantic data models
│   │
│   ├── ingestion/            # Image discovery
│   │   ├── discover.py       # Recursive image finder
│   │   └── metadata.py       # EXIF extraction
│   │
│   ├── config/               # Configuration
│   │   ├── loader.py         # YAML config loading
│   │   └── schema.py         # Config validation
│   │
│   └── output/               # Output generation
│       └── csv_writer.py     # CSV output
│
├── configs/                  # Configuration files
│   └── default.yaml          # Default scoring weights
│
├── tests/                    # Test suite
│   ├── test_cache.py
│   ├── test_config.py
│   ├── test_explanations.py
│   └── test_reducer.py
│
├── docs/                     # Documentation
│   └── COMPETITIVE_RESEARCH.md
│
└── .claude/                  # Claude Code configuration
    ├── settings.json         # Hooks and commands
    └── skills/               # Context-aware skills
        ├── technical/
        ├── runbooks/
        └── reference/
```

## Key Files

| File | Purpose |
|------|---------|
| `calibrate.py` | Main entry point for batch scoring |
| `serve_viewer.py` | Web UI for reviewing results |
| `photo_score/scoring/composite.py` | Multi-model scoring engine |
| `photo_score/inference/client.py` | OpenRouter API client |
| `photo_score/inference/prompts_v2.py` | All prompt templates |
| `photo_score/storage/cache.py` | SQLite caching |

## Data Flow

```
calibrate.py
    └── CompositeScorer (composite.py)
            ├── OpenRouterClient (client.py)
            │       ├── Feature extraction
            │       ├── Aesthetic scoring (2 models)
            │       ├── Technical scoring (2 models)
            │       ├── Metadata extraction
            │       └── Critique generation
            └── Cache (cache.py)
                    └── ~/.photo_score/cache.db
```
