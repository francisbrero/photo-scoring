from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import auth, billing, inference, photo_serve, photos


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup: validate settings are loadable
    settings = get_settings()
    if settings.debug:
        print("Debug mode enabled")
    yield
    # Shutdown: cleanup if needed


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Photo Score API",
        description="Cloud backend for Photo Scoring - authentication, inference, and sync",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint for Railway deployment."""
        return {"status": "healthy", "version": "0.1.0"}

    # Include routers
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(billing.router, prefix="/billing", tags=["billing"])
    app.include_router(inference.router, prefix="/inference", tags=["inference"])
    app.include_router(photos.router, prefix="/api/photos", tags=["photos"])
    app.include_router(photo_serve.router, prefix="/photos", tags=["photos"])

    return app


app = create_app()
