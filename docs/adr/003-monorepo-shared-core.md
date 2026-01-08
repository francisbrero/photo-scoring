# ADR-003: Monorepo with Shared Core Package

## Status

Accepted

## Date

2024-01-01

## Context

Photo Scorer needs to run in multiple environments:
- **CLI**: Power users running locally
- **Desktop App**: Casual users wanting a GUI
- **Cloud API**: Team access, credit-based billing
- **Web Viewer**: Browser-based result exploration

All environments need identical scoring logic. Divergence would create inconsistent results and maintenance burden.

## Decision

Adopt a **monorepo structure** with a shared Python core package.

### Repository Structure

```
photo-scoring/
├── photo_score/           # Shared core (Python package)
│   ├── cli.py            # Typer CLI entry point
│   ├── ingestion/        # Image discovery, EXIF
│   ├── inference/        # OpenRouter client, prompts
│   ├── scoring/          # Reducer, explanations
│   ├── storage/          # SQLite cache
│   ├── config/           # YAML loading
│   └── output/           # CSV writer
├── packages/
│   ├── api/              # FastAPI cloud backend
│   ├── desktop/          # Electron + React app
│   └── webapp/           # Web interface (React/Vite)
├── configs/              # Scoring configuration YAMLs
├── tests/                # Pytest test suite
└── docs/                 # Documentation + ADRs
```

### Sharing Strategy

1. **CLI**: Directly imports `photo_score` package
2. **Desktop**: Python sidecar bundles `photo_score` via PyInstaller
3. **Cloud API**: FastAPI imports `photo_score` for scoring logic
4. **Web Viewer**: Standalone server embeds viewer, uses `photo_score` for data

### Package Management

- Root `pyproject.toml` defines `photo_score` package
- `uv` for fast, deterministic dependency management
- Each `packages/` subdirectory has its own dependencies where needed

## Consequences

### Positive

- **Single source of truth**: Scoring logic identical everywhere
- **Reduced maintenance**: Fix once, deploy everywhere
- **Consistent results**: Users get same scores on desktop vs cloud
- **Easier testing**: Test core package, confidence in all platforms
- **Code reuse**: 80%+ of logic shared

### Negative

- **Coordination required**: Changes to core affect all platforms
- **Build complexity**: Multiple build targets (PyInstaller, Docker, npm)
- **Version alignment**: Must keep platforms in sync
- **Larger repo**: All code in one place

### Neutral

- Clear separation between core logic and platform-specific code
- Desktop and cloud can evolve UI independently
- Enables gradual rollout of features

## Alternatives Considered

### 1. Separate Repositories
- **Rejected**: Would lead to code duplication
- Scoring logic would drift between platforms
- Harder to ensure consistency

### 2. Published PyPI Package
- **Rejected**: Too slow for iteration
- Would need to publish for every change
- Version management overhead

### 3. Git Submodules
- **Rejected**: Complex workflow
- Submodule sync issues are common
- Monorepo is simpler

### 4. Microservices (API Only)
- **Rejected**: Desktop needs offline capability
- Can't call cloud API without internet
- Latency would hurt UX

## References

- Root `pyproject.toml`: Package definition
- `packages/api/`: FastAPI implementation
- `packages/desktop/`: Electron app with sidecar
- `packages/webapp/`: React web interface
