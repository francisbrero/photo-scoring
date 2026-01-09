# ADR-005: Desktop App with Electron + Python Sidecar

## Status

Accepted

## Date

2024-01-01

## Context

We need a cross-platform desktop application that:
- Works offline (no internet required after initial scoring)
- Has native file system access for photo discovery
- Shares scoring logic with CLI and cloud
- Provides a modern, responsive UI

Options considered:
1. Pure Electron with Node.js scoring (rewrite Python logic)
2. Electron + Python sidecar (spawn Python process)
3. Tauri + Rust (rewrite in Rust)
4. PyQt/Tkinter (pure Python GUI)

## Decision

Use **Electron for UI** with a **Python FastAPI sidecar** for scoring logic.

### Architecture

```
┌─────────────────────────────────────────┐
│           Electron Main Process         │
│  ┌─────────────────────────────────┐   │
│  │     React + Vite Frontend       │   │
│  │     (TypeScript, Tailwind)      │   │
│  └─────────────────────────────────┘   │
│                  │ IPC                  │
│                  ▼                      │
│  ┌─────────────────────────────────┐   │
│  │     Electron IPC Handlers       │   │
│  │     (spawn/manage sidecar)      │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
                   │ HTTP (localhost)
                   ▼
┌─────────────────────────────────────────┐
│         Python Sidecar (FastAPI)        │
│  ┌─────────────────────────────────┐   │
│  │      photo_score package        │   │
│  │  (inference, scoring, cache)    │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Sidecar Details

- **Bundled with PyInstaller**: Single executable, no Python install required
- **Local HTTP server**: Runs on localhost port (e.g., 8765)
- **REST API**: Same endpoints as cloud API where applicable
- **Lifecycle**: Spawned on app start, killed on app quit

### Communication Flow

1. Electron spawns sidecar process on startup
2. React UI makes HTTP requests to `localhost:8765`
3. Sidecar uses `photo_score` package for all logic
4. Results cached in `~/.photo_score/cache.db`
5. UI updates via polling or WebSocket (future)

### Packaging

- **macOS**: `.dmg` with universal binary (Apple Silicon + Intel)
- **Windows**: `.exe` installer via electron-builder
- **Linux**: `.AppImage` for broad compatibility
- **Sidecar**: PyInstaller spec file defines bundling

## Consequences

### Positive

- **Code reuse**: 100% of Python scoring logic shared
- **Familiar tech**: React/TypeScript for web developers
- **Cross-platform**: Single codebase for macOS/Windows/Linux
- **Offline capable**: Sidecar runs locally, no cloud dependency
- **Native features**: File dialogs, system notifications, menu bar

### Negative

- **Process management**: Must handle sidecar lifecycle
- **Bundle size**: PyInstaller adds ~100MB to app size
- **Startup time**: Sidecar needs 2-3s to initialize
- **Two runtimes**: Both Node.js and Python in bundle
- **IPC complexity**: HTTP between Electron and Python

### Neutral

- Can update sidecar independently of Electron shell
- Debugging requires monitoring both processes
- Same API contract as cloud (easier to add sync features)

## Alternatives Considered

### 1. Pure Electron (Rewrite in Node.js)
- **Rejected**: Would duplicate all Python logic
- Vision model client, scoring, caching all need rewrite
- Maintenance nightmare keeping two implementations in sync

### 2. Tauri + Rust
- **Rejected**: Would require Rust rewrite of core logic
- Team expertise is Python, not Rust
- Smaller bundle size not worth rewrite cost

### 3. PyQt / Tkinter
- **Rejected**: Dated UI toolkit, limited styling
- Harder to find developers
- Web-like UI not achievable

### 4. Web App Only (No Desktop)
- **Rejected**: Offline requirement critical
- Users want to score photos without uploading
- Privacy concerns with cloud-only

### 5. WASM (Pyodide)
- **Rejected**: Vision model calls need native HTTP
- Performance concerns with large images
- Limited library support

## References

- `packages/desktop/`: Electron app source
- `packages/desktop/sidecar/`: Python sidecar FastAPI
- `packages/desktop/sidecar/sidecar.spec`: PyInstaller config
- `packages/desktop/electron-builder.yml`: Build configuration
