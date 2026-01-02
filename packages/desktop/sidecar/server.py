"""FastAPI sidecar server for Photo Scoring desktop app."""

import argparse
import sys
from pathlib import Path

# Determine if we're running as a PyInstaller bundle
if getattr(sys, "frozen", False):
    # Running as compiled executable
    bundle_dir = Path(sys._MEIPASS)
    root_path = bundle_dir
    sys.path.insert(0, str(bundle_dir))
else:
    # Running in development
    root_path = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(root_path))

# Load environment variables from root .env file
from dotenv import load_dotenv

env_file = root_path / ".env"
if env_file.exists():
    load_dotenv(env_file)

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from handlers.photos import router as photos_router  # noqa: E402
from handlers.inference import router as inference_router  # noqa: E402
from handlers.sync import router as sync_router  # noqa: E402
from handlers.settings import router as settings_router  # noqa: E402
from handlers.auth import router as auth_router  # noqa: E402

app = FastAPI(
    title="Photo Scorer Sidecar",
    description="Local backend for Photo Scorer desktop app",
    version="0.1.0",
)

# Allow CORS from Electron renderer
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(photos_router, prefix="/api/photos", tags=["photos"])
app.include_router(inference_router, prefix="/api/inference", tags=["inference"])
app.include_router(sync_router, prefix="/api/sync", tags=["sync"])
app.include_router(settings_router, prefix="/api/settings", tags=["settings"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])


@app.get("/health")
async def health_check():
    """Health check endpoint for Electron to verify sidecar is running."""
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/api/status")
async def get_status():
    """Get detailed status of the sidecar."""
    from photo_score.storage.cache import Cache

    cache = Cache()
    cache_stats = cache.get_stats() if hasattr(cache, "get_stats") else {}

    return {
        "status": "running",
        "cache": cache_stats,
    }


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="Photo Scoring Sidecar Server")
    parser.add_argument("--port", type=int, default=9000, help="Port to run on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
