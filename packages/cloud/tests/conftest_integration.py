"""Integration test fixtures using local Supabase.

These tests require local Supabase to be running:
    supabase start

Run integration tests with:
    pytest tests/ -m integration
"""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from supabase import Client, create_client

# Local Supabase credentials (from `supabase status`)
LOCAL_SUPABASE_URL = "http://127.0.0.1:54321"
LOCAL_SUPABASE_SERVICE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0."
    "EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"
)
LOCAL_SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9."
    "CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"
)
LOCAL_JWT_SECRET = "super-secret-jwt-token-with-at-least-32-characters-long"


def is_supabase_running() -> bool:
    """Check if local Supabase is running."""
    import httpx

    try:
        response = httpx.get(f"{LOCAL_SUPABASE_URL}/rest/v1/", timeout=2)
        return response.status_code in (200, 401)  # 401 means it's running but needs auth
    except Exception:
        return False


# Skip integration tests if Supabase is not running
requires_supabase = pytest.mark.skipif(
    not is_supabase_running(), reason="Local Supabase not running. Start with: supabase start"
)


@pytest.fixture
def supabase_admin() -> Client:
    """Create Supabase admin client with service role key."""
    if not is_supabase_running():
        pytest.skip("Local Supabase not running")
    return create_client(LOCAL_SUPABASE_URL, LOCAL_SUPABASE_SERVICE_KEY)


@pytest.fixture
def integration_client(monkeypatch):
    """Create test client connected to local Supabase."""
    from api.config import get_settings

    get_settings.cache_clear()

    monkeypatch.setenv("SUPABASE_URL", LOCAL_SUPABASE_URL)
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", LOCAL_SUPABASE_SERVICE_KEY)
    monkeypatch.setenv("SUPABASE_JWT_SECRET", LOCAL_JWT_SECRET)
    monkeypatch.setenv("OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY", "test-key"))
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_fake")

    from api.main import create_app

    app = create_app()
    return TestClient(app)


@pytest.fixture
def test_user(supabase_admin) -> dict:
    """Create a test user in local Supabase and return user info."""
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"

    # Create user via admin API
    response = supabase_admin.auth.admin.create_user(
        {
            "email": email,
            "password": password,
            "email_confirm": True,  # Auto-confirm email
        }
    )

    user = response.user
    yield {
        "id": user.id,
        "email": email,
        "password": password,
    }

    # Cleanup: delete user after test
    try:
        supabase_admin.auth.admin.delete_user(user.id)
    except Exception:
        pass


@pytest.fixture
def test_user_token(test_user) -> str:
    """Create a valid JWT token for the test user."""
    payload = {
        "sub": test_user["id"],
        "email": test_user["email"],
        "role": "authenticated",
        "aud": "authenticated",
        "iat": 1704067200,
        "exp": 1988150400,  # Far future
    }
    return jwt.encode(payload, LOCAL_JWT_SECRET, algorithm="HS256")


@pytest.fixture
def auth_headers(test_user_token) -> dict:
    """Return authorization headers for test user."""
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture
def sample_jpeg_bytes() -> bytes:
    """Create a minimal valid JPEG image for testing."""
    # Minimal valid JPEG (1x1 red pixel)
    return bytes(
        [
            0xFF,
            0xD8,
            0xFF,
            0xE0,
            0x00,
            0x10,
            0x4A,
            0x46,
            0x49,
            0x46,
            0x00,
            0x01,
            0x01,
            0x00,
            0x00,
            0x01,
            0x00,
            0x01,
            0x00,
            0x00,
            0xFF,
            0xDB,
            0x00,
            0x43,
            0x00,
            0x08,
            0x06,
            0x06,
            0x07,
            0x06,
            0x05,
            0x08,
            0x07,
            0x07,
            0x07,
            0x09,
            0x09,
            0x08,
            0x0A,
            0x0C,
            0x14,
            0x0D,
            0x0C,
            0x0B,
            0x0B,
            0x0C,
            0x19,
            0x12,
            0x13,
            0x0F,
            0x14,
            0x1D,
            0x1A,
            0x1F,
            0x1E,
            0x1D,
            0x1A,
            0x1C,
            0x1C,
            0x20,
            0x24,
            0x2E,
            0x27,
            0x20,
            0x22,
            0x2C,
            0x23,
            0x1C,
            0x1C,
            0x28,
            0x37,
            0x29,
            0x2C,
            0x30,
            0x31,
            0x34,
            0x34,
            0x34,
            0x1F,
            0x27,
            0x39,
            0x3D,
            0x38,
            0x32,
            0x3C,
            0x2E,
            0x33,
            0x34,
            0x32,
            0xFF,
            0xC0,
            0x00,
            0x0B,
            0x08,
            0x00,
            0x01,
            0x00,
            0x01,
            0x01,
            0x01,
            0x11,
            0x00,
            0xFF,
            0xC4,
            0x00,
            0x1F,
            0x00,
            0x00,
            0x01,
            0x05,
            0x01,
            0x01,
            0x01,
            0x01,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x01,
            0x02,
            0x03,
            0x04,
            0x05,
            0x06,
            0x07,
            0x08,
            0x09,
            0x0A,
            0x0B,
            0xFF,
            0xC4,
            0x00,
            0xB5,
            0x10,
            0x00,
            0x02,
            0x01,
            0x03,
            0x03,
            0x02,
            0x04,
            0x03,
            0x05,
            0x05,
            0x04,
            0x04,
            0x00,
            0x00,
            0x01,
            0x7D,
            0x01,
            0x02,
            0x03,
            0x00,
            0x04,
            0x11,
            0x05,
            0x12,
            0x21,
            0x31,
            0x41,
            0x06,
            0x13,
            0x51,
            0x61,
            0x07,
            0x22,
            0x71,
            0x14,
            0x32,
            0x81,
            0x91,
            0xA1,
            0x08,
            0x23,
            0x42,
            0xB1,
            0xC1,
            0x15,
            0x52,
            0xD1,
            0xF0,
            0x24,
            0x33,
            0x62,
            0x72,
            0x82,
            0x09,
            0x0A,
            0x16,
            0x17,
            0x18,
            0x19,
            0x1A,
            0x25,
            0x26,
            0x27,
            0x28,
            0x29,
            0x2A,
            0x34,
            0x35,
            0x36,
            0x37,
            0x38,
            0x39,
            0x3A,
            0x43,
            0x44,
            0x45,
            0x46,
            0x47,
            0x48,
            0x49,
            0x4A,
            0x53,
            0x54,
            0x55,
            0x56,
            0x57,
            0x58,
            0x59,
            0x5A,
            0x63,
            0x64,
            0x65,
            0x66,
            0x67,
            0x68,
            0x69,
            0x6A,
            0x73,
            0x74,
            0x75,
            0x76,
            0x77,
            0x78,
            0x79,
            0x7A,
            0x83,
            0x84,
            0x85,
            0x86,
            0x87,
            0x88,
            0x89,
            0x8A,
            0x92,
            0x93,
            0x94,
            0x95,
            0x96,
            0x97,
            0x98,
            0x99,
            0x9A,
            0xA2,
            0xA3,
            0xA4,
            0xA5,
            0xA6,
            0xA7,
            0xA8,
            0xA9,
            0xAA,
            0xB2,
            0xB3,
            0xB4,
            0xB5,
            0xB6,
            0xB7,
            0xB8,
            0xB9,
            0xBA,
            0xC2,
            0xC3,
            0xC4,
            0xC5,
            0xC6,
            0xC7,
            0xC8,
            0xC9,
            0xCA,
            0xD2,
            0xD3,
            0xD4,
            0xD5,
            0xD6,
            0xD7,
            0xD8,
            0xD9,
            0xDA,
            0xE1,
            0xE2,
            0xE3,
            0xE4,
            0xE5,
            0xE6,
            0xE7,
            0xE8,
            0xE9,
            0xEA,
            0xF1,
            0xF2,
            0xF3,
            0xF4,
            0xF5,
            0xF6,
            0xF7,
            0xF8,
            0xF9,
            0xFA,
            0xFF,
            0xDA,
            0x00,
            0x08,
            0x01,
            0x01,
            0x00,
            0x00,
            0x3F,
            0x00,
            0xFB,
            0xD5,
            0xDB,
            0x20,
            0xA8,
            0xA0,
            0x02,
            0x80,
            0x0A,
            0x00,
            0x28,
            0x00,
            0xA0,
            0x02,
            0x80,
            0x0A,
            0x00,
            0xFF,
            0xD9,
        ]
    )


@pytest.fixture
def cleanup_storage(supabase_admin, test_user):
    """Clean up storage after tests."""
    yield
    # Delete all files for test user
    try:
        files = supabase_admin.storage.from_("photos").list(test_user["id"])
        if files:
            paths = [f"{test_user['id']}/{f['name']}" for f in files]
            supabase_admin.storage.from_("photos").remove(paths)
    except Exception:
        pass


@pytest.fixture
def mock_openrouter(monkeypatch):
    """Mock all OpenRouter service methods to avoid API calls.

    Returns mock responses that simulate rich critique generation.
    """
    from api.services import openrouter

    async def mock_analyze_image(self, image_data, image_hash):
        return {
            "composition": 0.7,
            "subject_strength": 0.8,
            "visual_appeal": 0.75,
            "sharpness": 0.9,
            "exposure_balance": 0.85,
            "noise_level": 0.1,
        }

    async def mock_analyze_metadata(self, image_data, image_hash):
        return {
            "description": "A test photograph showing a landscape scene.",
            "location_name": "Test Location",
            "location_country": "Test Country",
        }

    async def mock_extract_features(self, image_data):
        return {
            "scene_type": "landscape",
            "main_subject": "mountain range with dramatic sky",
            "subject_position": "center",
            "background": "clean",
            "lighting": "golden_hour",
            "color_palette": "warm",
            "depth_of_field": "deep",
            "motion": "static",
            "human_presence": "none",
            "text_or_signs": False,
            "weather_visible": "clear",
            "time_of_day": "golden_hour",
            "technical_issues": [],
            "notable_elements": ["dramatic clouds", "mountain peaks", "warm light"],
            "estimated_location_type": "mountain",
        }

    async def mock_generate_critique(self, image_data, features, attributes, final_score):
        return {
            "summary": (
                "This landscape photograph captures a stunning mountain scene with excellent "
                "golden hour lighting. The composition effectively uses the rule of thirds, "
                "though the foreground could benefit from a stronger anchor element."
            ),
            "working_well": [
                "The golden hour lighting creates beautiful warm tones across the mountain "
                "peaks, adding depth and dimension to the scene.",
                "Strong technical execution with excellent sharpness throughout the frame "
                "and well-controlled exposure in the challenging lighting conditions.",
            ],
            "could_improve": [
                "The foreground lacks a compelling anchor element - consider including "
                "rocks, flowers, or leading lines to draw the viewer into the scene.",
                "The horizon is placed near the center; try positioning it on the upper "
                "or lower third for a more dynamic composition.",
            ],
            "key_recommendation": (
                "Return during different lighting conditions or find a foreground element "
                "like interesting rocks or wildflowers to create depth and lead the "
                "viewer's eye through the frame."
            ),
        }

    monkeypatch.setattr(openrouter.OpenRouterService, "analyze_image", mock_analyze_image)
    monkeypatch.setattr(
        openrouter.OpenRouterService, "analyze_image_metadata", mock_analyze_metadata
    )
    monkeypatch.setattr(openrouter.OpenRouterService, "extract_features", mock_extract_features)
    monkeypatch.setattr(openrouter.OpenRouterService, "generate_critique", mock_generate_critique)

    return {
        "analyze_image": mock_analyze_image,
        "analyze_metadata": mock_analyze_metadata,
        "extract_features": mock_extract_features,
        "generate_critique": mock_generate_critique,
    }
