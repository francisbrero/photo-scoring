"""Shared test fixtures and configuration."""

import pytest
from fastapi.testclient import TestClient
from jose import jwt

# Service key must be a valid JWT format for Supabase client validation
FAKE_SERVICE_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRlc3QiLCJyb2xlIjoic2VydmljZV9yb2xlIiwiaWF0IjoxNjQxNzY5MjAwLCJleHAiOjE5NTczNDUyMDB9."
    "test_signature_placeholder"
)


@pytest.fixture
def client(monkeypatch):
    """Create test client with mocked settings."""
    # Clear cached settings to ensure fresh config
    from api.config import get_settings

    get_settings.cache_clear()

    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_123")

    from api.main import create_app

    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_token():
    """Create a valid JWT token for testing."""
    payload = {
        "sub": "test-user-id-123",
        "email": "test@example.com",
        "role": "authenticated",
        "aud": "authenticated",
    }
    return jwt.encode(payload, "test-jwt-secret", algorithm="HS256")
