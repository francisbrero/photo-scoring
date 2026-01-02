# Photo Scoring Desktop App

Electron desktop application with React frontend and Python sidecar for local photo scoring.

## Architecture

```
packages/desktop/
├── main/           # Electron main process (TypeScript)
├── renderer/       # React frontend (Vite + TypeScript)
├── sidecar/        # Python FastAPI backend
└── resources/      # App icons and assets
```

## Development Setup

### Prerequisites

- Node.js 20+
- Python 3.11+
- uv (Python package manager)

### Install Dependencies

```bash
# Install Node dependencies
npm install

# Install Python dependencies for sidecar
cd sidecar
uv sync
cd ..
```

### Run in Development

1. Start the Python sidecar (in one terminal):
```bash
cd sidecar
uv run uvicorn server:app --port 9000 --reload
```

2. Start the Electron app (in another terminal):
```bash
npm run dev
```

Then run `npm run start` to launch Electron.

### Environment Variables

Create `renderer/.env` based on `renderer/.env.example`:

```bash
cp renderer/.env.example renderer/.env
```

Configure Supabase credentials for cloud sync (optional).

## Building for Distribution

### Build All Platforms

```bash
npm run dist
```

### Platform-Specific Builds

```bash
npm run dist:mac     # macOS .dmg
npm run dist:win     # Windows .exe
npm run dist:linux   # Linux .AppImage
```

### Bundling Python Sidecar

Before building for distribution, bundle the Python sidecar with PyInstaller:

```bash
cd sidecar
pip install pyinstaller
pyinstaller --onedir --name photoscore-sidecar server.py
```

Copy the output to `sidecar-dist/` for inclusion in the Electron build.

## Project Structure

### Electron Main Process (`main/`)

- `index.ts` - App entry, window management, menu
- `sidecar.ts` - Python process lifecycle management
- `ipc.ts` - IPC handlers for renderer communication
- `preload.ts` - Context bridge for secure renderer APIs

### React Renderer (`renderer/`)

- `src/App.tsx` - Main application component
- `src/components/` - UI components (PhotoBrowser, ScoreViewer, Layout)
- `src/hooks/` - React hooks (usePhotos, useAuth)
- `src/services/` - API clients (sidecar, cloud)
- `src/types/` - TypeScript type definitions

### Python Sidecar (`sidecar/`)

- `server.py` - FastAPI application
- `handlers/photos.py` - Image discovery and thumbnails
- `handlers/inference.py` - Scoring via photo_score core
- `handlers/sync.py` - Cloud sync operations

## API Endpoints (Sidecar)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/photos/discover` | GET | Discover images in directory |
| `/api/photos/thumbnail` | GET | Generate thumbnail |
| `/api/photos/metadata` | GET | Get image metadata |
| `/api/inference/score` | POST | Score an image |
| `/api/inference/rescore` | POST | Rescore from cache |
| `/api/inference/attributes` | GET | Get cached attributes |
| `/api/sync/status` | GET | Get sync status |
| `/api/sync/start` | POST | Start cloud sync |

## Acceptance Criteria

- [x] App launches on macOS/Windows/Linux
- [x] Python sidecar starts and responds to health check
- [x] Can browse local photos
- [x] Thumbnails display correctly
- [x] Login/logout works with Supabase (when configured)
- [ ] App builds for distribution (requires icon assets)
