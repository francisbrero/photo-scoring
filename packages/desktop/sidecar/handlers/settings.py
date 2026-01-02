"""Settings handlers for API key management."""

import os
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Settings file location - use user's home directory
SETTINGS_DIR = Path.home() / ".photo_score"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


def _ensure_settings_dir():
    """Ensure the settings directory exists."""
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)


def _load_settings() -> dict:
    """Load settings from file."""
    _ensure_settings_dir()
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_settings(settings: dict):
    """Save settings to file."""
    _ensure_settings_dir()
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def load_api_key_to_env():
    """Load API key from settings file into environment variable."""
    settings = _load_settings()
    api_key = settings.get("openrouter_api_key")
    if api_key:
        os.environ["OPENROUTER_API_KEY"] = api_key


class ApiKeyRequest(BaseModel):
    """Request to set API key."""

    api_key: str


class ApiKeyStatus(BaseModel):
    """API key status response."""

    is_set: bool
    masked_key: str | None = None


@router.get("/api-key", response_model=ApiKeyStatus)
async def get_api_key_status():
    """Check if API key is configured."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if api_key:
        # Mask all but last 4 characters
        masked = "*" * (len(api_key) - 4) + api_key[-4:] if len(api_key) > 4 else "****"
        return ApiKeyStatus(is_set=True, masked_key=masked)
    return ApiKeyStatus(is_set=False)


@router.post("/api-key")
async def set_api_key(request: ApiKeyRequest):
    """Set the OpenRouter API key."""
    if not request.api_key or len(request.api_key) < 10:
        raise HTTPException(status_code=400, detail="Invalid API key")

    # Set in environment
    os.environ["OPENROUTER_API_KEY"] = request.api_key

    # Persist to settings file
    settings = _load_settings()
    settings["openrouter_api_key"] = request.api_key
    _save_settings(settings)

    return {"status": "ok", "message": "API key saved successfully"}


@router.delete("/api-key")
async def delete_api_key():
    """Remove the API key."""
    if "OPENROUTER_API_KEY" in os.environ:
        del os.environ["OPENROUTER_API_KEY"]

    settings = _load_settings()
    if "openrouter_api_key" in settings:
        del settings["openrouter_api_key"]
        _save_settings(settings)

    return {"status": "ok", "message": "API key removed"}


@router.get("/status")
async def get_settings_status():
    """Get overall settings status."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    return {
        "api_key_configured": bool(api_key),
        "settings_dir": str(SETTINGS_DIR),
    }
