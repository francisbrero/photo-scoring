"""Authentication handler for Photo Scoring cloud API."""

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Settings file location - use user's home directory
SETTINGS_DIR = Path.home() / ".photo_score"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

# Cloud API URL - can be overridden via environment variable
CLOUD_API_URL = os.environ.get(
    "PHOTO_SCORE_API_URL", "https://photo-score-api.onrender.com"
)


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


def get_auth_token() -> str | None:
    """Get the stored auth token."""
    settings = _load_settings()
    return settings.get("auth_token")


def get_user_info() -> dict | None:
    """Get stored user info."""
    settings = _load_settings()
    return settings.get("user_info")


class LoginRequest(BaseModel):
    """Login request body."""

    email: str
    password: str


class SignupRequest(BaseModel):
    """Signup request body."""

    email: str
    password: str


class AuthStatus(BaseModel):
    """Authentication status response."""

    authenticated: bool
    user_email: str | None = None
    credits: int | None = None


class AuthResponse(BaseModel):
    """Authentication response after login/signup."""

    authenticated: bool
    user_email: str
    credits: int
    message: str


@router.get("/status", response_model=AuthStatus)
async def get_auth_status():
    """Check if user is authenticated."""
    import httpx

    token = get_auth_token()
    if not token:
        return AuthStatus(authenticated=False)

    # Verify token with cloud API
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CLOUD_API_URL}/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                return AuthStatus(
                    authenticated=True,
                    user_email=data.get("email"),
                    credits=data.get("credits", 0),
                )
            else:
                # Token invalid, clear it
                settings = _load_settings()
                settings.pop("auth_token", None)
                settings.pop("user_info", None)
                _save_settings(settings)
                return AuthStatus(authenticated=False)
    except Exception:
        # Network error - check cached user info
        user_info = get_user_info()
        if user_info:
            return AuthStatus(
                authenticated=True,
                user_email=user_info.get("email"),
                credits=user_info.get("credits"),
            )
        return AuthStatus(authenticated=False)


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login with email and password."""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CLOUD_API_URL}/api/auth/login",
                json={"email": request.email, "password": request.password},
                timeout=30.0,
            )

            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")

                # Get user info
                me_response = await client.get(
                    f"{CLOUD_API_URL}/api/auth/me",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0,
                )

                if me_response.status_code == 200:
                    user_data = me_response.json()

                    # Store auth token and user info
                    settings = _load_settings()
                    settings["auth_token"] = token
                    settings["user_info"] = {
                        "email": user_data.get("email"),
                        "credits": user_data.get("credits", 0),
                        "user_id": user_data.get("id"),
                    }
                    _save_settings(settings)

                    return AuthResponse(
                        authenticated=True,
                        user_email=user_data.get("email"),
                        credits=user_data.get("credits", 0),
                        message="Login successful",
                    )

            elif response.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid email or password",
                )
            else:
                try:
                    error_detail = response.json().get("detail", "Login failed")
                except Exception:
                    error_detail = response.text or "Login failed"
                raise HTTPException(
                    status_code=response.status_code, detail=error_detail
                )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to Photo Scorer service: {str(e)}",
        )


@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
    """Create a new account."""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CLOUD_API_URL}/api/auth/signup",
                json={"email": request.email, "password": request.password},
                timeout=30.0,
            )

            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")

                # Get user info
                me_response = await client.get(
                    f"{CLOUD_API_URL}/api/auth/me",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0,
                )

                if me_response.status_code == 200:
                    user_data = me_response.json()

                    # Store auth token and user info
                    settings = _load_settings()
                    settings["auth_token"] = token
                    settings["user_info"] = {
                        "email": user_data.get("email"),
                        "credits": user_data.get("credits", 0),
                        "user_id": user_data.get("id"),
                    }
                    _save_settings(settings)

                    return AuthResponse(
                        authenticated=True,
                        user_email=user_data.get("email"),
                        credits=user_data.get("credits", 0),
                        message="Account created! You have 5 free trial credits.",
                    )

            elif response.status_code == 400:
                try:
                    error_detail = response.json().get("detail", "Signup failed")
                except Exception:
                    error_detail = response.text or "Signup failed"
                raise HTTPException(status_code=400, detail=error_detail)
            else:
                try:
                    error_detail = response.json().get("detail", "Signup failed")
                except Exception:
                    error_detail = response.text or "Signup failed"
                raise HTTPException(
                    status_code=response.status_code, detail=error_detail
                )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to Photo Scorer service: {str(e)}",
        )


@router.post("/logout")
async def logout():
    """Log out and clear stored credentials."""
    settings = _load_settings()
    settings.pop("auth_token", None)
    settings.pop("user_info", None)
    _save_settings(settings)
    return {"status": "ok", "message": "Logged out successfully"}


@router.get("/credits")
async def get_credits():
    """Get current credit balance."""
    import httpx

    token = get_auth_token()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CLOUD_API_URL}/api/billing/balance",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                # Update cached credits
                settings = _load_settings()
                if "user_info" in settings:
                    settings["user_info"]["credits"] = data.get("balance", 0)
                    _save_settings(settings)
                return {"credits": data.get("balance", 0)}
            elif response.status_code == 401:
                raise HTTPException(
                    status_code=401, detail="Session expired. Please log in again."
                )
            else:
                raise HTTPException(
                    status_code=response.status_code, detail="Failed to get credits"
                )

    except httpx.RequestError as e:
        # Return cached credits if available
        user_info = get_user_info()
        if user_info and "credits" in user_info:
            return {"credits": user_info["credits"], "cached": True}
        raise HTTPException(
            status_code=503, detail=f"Cannot connect to service: {str(e)}"
        )
