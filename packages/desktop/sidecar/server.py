"""FastAPI sidecar server for Photo Scoring desktop app."""

import sys
from pathlib import Path

# Add parent directory to path to import photo_score package
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from handlers.photos import router as photos_router
from handlers.inference import router as inference_router
from handlers.sync import router as sync_router

app = FastAPI(
    title="Photo Scoring Sidecar",
    description="Local backend for Photo Scoring desktop app",
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
