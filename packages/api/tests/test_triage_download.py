"""Tests for the triage download endpoint."""

import io
import zipfile
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jose import jwt

# Service key must be a valid JWT format for Supabase client validation
FAKE_SERVICE_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRlc3QiLCJyb2xlIjoic2VydmljZV9yb2xlIiwiaWF0IjoxNjQxNzY5MjAwLCJleHAiOjE5NTczNDUyMDB9."
    "test_signature_placeholder"
)

JOB_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
USER_ID = "test-user-id-123"


@pytest.fixture
def client(monkeypatch):
    """Create test client with mocked settings."""
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
    from fastapi.testclient import TestClient

    return TestClient(app)


@pytest.fixture
def auth_token():
    """Create a valid JWT token for testing."""
    payload = {
        "sub": USER_ID,
        "email": "test@example.com",
        "role": "authenticated",
        "aud": "authenticated",
    }
    return jwt.encode(payload, "test-jwt-secret", algorithm="HS256")


@pytest.fixture
def auth_headers(auth_token):
    """Create authorization headers."""
    return {"Authorization": f"Bearer {auth_token}"}


def _completed_job():
    return {
        "id": JOB_ID,
        "status": "completed",
        "user_id": USER_ID,
        "created_at": datetime.now(UTC).isoformat(),
    }


def test_download_requires_auth(client):
    """GET without token returns 401."""
    response = client.get(f"/api/triage/{JOB_ID}/download")
    assert response.status_code == 401


@patch("api.routers.triage.TriageService")
def test_download_job_not_found(mock_svc_cls, client, auth_headers):
    """Valid auth, nonexistent job returns 404."""
    instance = mock_svc_cls.return_value
    instance.get_job = AsyncMock(return_value=None)

    response = client.get(f"/api/triage/{JOB_ID}/download", headers=auth_headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@patch("api.routers.triage.TriageService")
def test_download_incomplete_job(mock_svc_cls, client, auth_headers):
    """Valid auth, non-completed job returns 400."""
    instance = mock_svc_cls.return_value
    instance.get_job = AsyncMock(
        return_value={
            "id": JOB_ID,
            "status": "processing",
            "user_id": USER_ID,
            "created_at": datetime.now(UTC).isoformat(),
        }
    )

    response = client.get(f"/api/triage/{JOB_ID}/download", headers=auth_headers)
    assert response.status_code == 400
    assert "completed" in response.json()["detail"].lower()


@patch("api.routers.triage.TriageService")
def test_download_no_selected_photos(mock_svc_cls, client, auth_headers):
    """Valid auth, completed job, no selections returns 400."""
    instance = mock_svc_cls.return_value
    instance.get_job = AsyncMock(return_value=_completed_job())
    instance.get_job_photos = AsyncMock(return_value=[])

    response = client.get(f"/api/triage/{JOB_ID}/download", headers=auth_headers)
    assert response.status_code == 400
    assert "no photos" in response.json()["detail"].lower()


@patch("api.routers.triage.TriageService")
def test_download_success(mock_svc_cls, client, auth_headers):
    """Valid auth, completed job with photos returns a valid ZIP."""
    instance = mock_svc_cls.return_value
    instance.get_job = AsyncMock(return_value=_completed_job())
    instance.get_job_photos = AsyncMock(
        return_value=[
            {
                "id": "photo-1",
                "original_filename": "sunset.jpg",
                "storage_path": f"triage/{USER_ID}/{JOB_ID}/001.jpg",
            },
            {
                "id": "photo-2",
                "original_filename": "mountain.jpg",
                "storage_path": f"triage/{USER_ID}/{JOB_ID}/002.jpg",
            },
        ]
    )

    # The download endpoint calls supabase.storage.from_("photos").download(path)
    # directly on the DI-injected supabase client.
    fake_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    mock_storage_bucket = MagicMock()
    mock_storage_bucket.download.return_value = fake_jpeg

    mock_supabase = MagicMock()
    mock_supabase.storage.from_.return_value = mock_storage_bucket

    from api.dependencies import get_supabase_client

    app = client.app
    app.dependency_overrides[get_supabase_client] = lambda: mock_supabase

    try:
        response = client.get(f"/api/triage/{JOB_ID}/download", headers=auth_headers)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "content-disposition" in response.headers
        assert f"triage_{JOB_ID[:8]}" in response.headers["content-disposition"]

        # Verify the response is a valid ZIP with expected files
        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer) as zf:
            names = zf.namelist()
            assert "sunset.jpg" in names
            assert "mountain.jpg" in names
    finally:
        app.dependency_overrides.pop(get_supabase_client, None)
