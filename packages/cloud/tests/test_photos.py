"""Tests for the photos endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt


@pytest.fixture
def client(monkeypatch):
    """Create test client with mocked settings."""
    # Set required environment variables before importing
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")
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
        "sub": "test-user-123",
        "email": "test@example.com",
        "role": "authenticated",
        "aud": "authenticated",
    }
    return jwt.encode(payload, "test-jwt-secret", algorithm="HS256")


@pytest.fixture
def auth_headers(auth_token):
    """Create authorization headers."""
    return {"Authorization": f"Bearer {auth_token}"}


def test_list_photos_requires_auth(client):
    """Test that photos endpoint requires authentication."""
    response = client.get("/api/photos")
    assert response.status_code == 401


def test_get_photo_requires_auth(client):
    """Test that single photo endpoint requires authentication."""
    response = client.get("/api/photos/some-photo-id")
    assert response.status_code == 401


def test_delete_photo_requires_auth(client):
    """Test that delete photo endpoint requires authentication."""
    response = client.delete("/api/photos/some-photo-id")
    assert response.status_code == 401


def test_photo_image_requires_auth(client):
    """Test that photo image endpoint requires authentication."""
    response = client.get("/api/photos/some-photo-id/image")
    assert response.status_code == 401


def test_serve_photo_requires_auth(client):
    """Test that photo serve endpoint requires authentication."""
    response = client.get("/photos/some/path/image.jpg")
    assert response.status_code == 401


def test_list_photos_pagination_params(client, auth_headers):
    """Test that list_photos accepts pagination parameters."""
    # Mock the supabase client
    with patch("api.dependencies.create_client") as mock_create:
        mock_supabase = MagicMock()
        mock_create.return_value = mock_supabase

        # Mock the query chain
        mock_query = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[], count=0)

        response = client.get(
            "/api/photos?limit=10&offset=20&sort_by=final_score&sort_order=asc",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 20
        assert data["photos"] == []
        assert data["has_more"] is False


def test_list_photos_invalid_sort_by(client, auth_headers):
    """Test that invalid sort_by parameter is rejected."""
    with patch("api.dependencies.create_client") as mock_create:
        mock_supabase = MagicMock()
        mock_create.return_value = mock_supabase

        response = client.get(
            "/api/photos?sort_by=invalid_field",
            headers=auth_headers,
        )
        assert response.status_code == 422  # Validation error


def test_list_photos_invalid_sort_order(client, auth_headers):
    """Test that invalid sort_order parameter is rejected."""
    with patch("api.dependencies.create_client") as mock_create:
        mock_supabase = MagicMock()
        mock_create.return_value = mock_supabase

        response = client.get(
            "/api/photos?sort_order=invalid",
            headers=auth_headers,
        )
        assert response.status_code == 422  # Validation error


def test_list_photos_limit_validation(client, auth_headers):
    """Test that limit parameter is validated."""
    with patch("api.dependencies.create_client") as mock_create:
        mock_supabase = MagicMock()
        mock_create.return_value = mock_supabase

        # Too high
        response = client.get(
            "/api/photos?limit=500",
            headers=auth_headers,
        )
        assert response.status_code == 422

        # Too low
        response = client.get(
            "/api/photos?limit=0",
            headers=auth_headers,
        )
        assert response.status_code == 422


def test_list_photos_with_data(client, auth_headers):
    """Test list_photos returns properly formatted data."""
    with patch("api.dependencies.create_client") as mock_create:
        mock_supabase = MagicMock()
        mock_create.return_value = mock_supabase

        # Sample photo data
        sample_photo = {
            "id": "photo-123",
            "storage_path": "photos/test-user-123/image.jpg",
            "final_score": 78.5,
            "aesthetic_score": 0.74,
            "technical_score": 0.87,
            "description": "A beautiful landscape",
            "explanation": "The composition shows strong balance",
            "improvements": "Consider adjusting exposure",
            "scene_type": "nature",
            "lighting": "natural_soft",
            "subject_position": "rule_of_thirds",
            "location_name": "Yosemite",
            "location_country": "USA",
            "features_json": {"color_palette": "warm"},
            "model_scores": {"qwen_aesthetic": 0.75, "gpt4o_aesthetic": 0.73},
            "created_at": "2025-01-01T00:00:00+00:00",
        }

        # Mock the query chain
        mock_query = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[sample_photo], count=1)

        response = client.get("/api/photos", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert len(data["photos"]) == 1

        photo = data["photos"][0]
        assert photo["id"] == "photo-123"
        assert photo["image_path"] == "photos/test-user-123/image.jpg"
        assert photo["final_score"] == 78.5
        assert photo["qwen_aesthetic"] == 0.75
        assert photo["gpt4o_aesthetic"] == 0.73


def _mock_empty_result(mock_supabase):
    """Helper to mock an empty database result."""
    mock_result = MagicMock(data=[])
    chain = mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value
    chain.execute.return_value = mock_result


def test_get_photo_not_found(client, auth_headers):
    """Test get_photo returns 404 for non-existent photo."""
    with patch("api.dependencies.create_client") as mock_create:
        mock_supabase = MagicMock()
        mock_create.return_value = mock_supabase

        # Mock empty result
        _mock_empty_result(mock_supabase)

        response = client.get("/api/photos/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404
        assert "Photo not found" in response.json()["detail"]


def test_delete_photo_not_found(client, auth_headers):
    """Test delete_photo returns 404 for non-existent photo."""
    with patch("api.dependencies.create_client") as mock_create:
        mock_supabase = MagicMock()
        mock_create.return_value = mock_supabase

        # Mock empty result
        _mock_empty_result(mock_supabase)

        response = client.delete("/api/photos/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404


def test_serve_photo_not_found(client, auth_headers):
    """Test serve_photo returns 404 for non-existent photo."""
    with patch("api.dependencies.create_client") as mock_create:
        mock_supabase = MagicMock()
        mock_create.return_value = mock_supabase

        # Mock empty result
        _mock_empty_result(mock_supabase)

        response = client.get(
            "/photos/nonexistent/path.jpg",
            headers=auth_headers,
            follow_redirects=False,
        )
        assert response.status_code == 404
        assert "Photo not found" in response.json()["detail"]


def test_serve_photo_redirect(client, auth_headers):
    """Test serve_photo redirects to signed URL."""
    with patch("api.dependencies.create_client") as mock_create:
        mock_supabase = MagicMock()
        mock_create.return_value = mock_supabase

        # Mock photo exists
        mock_result = MagicMock(data=[{"id": "photo-123"}])
        chain = mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value
        chain.execute.return_value = mock_result

        # Mock signed URL generation
        mock_supabase.storage.from_.return_value.create_signed_url.return_value = {
            "signedURL": "https://storage.supabase.co/signed-url-here"
        }

        response = client.get(
            "/photos/photos/test-user-123/image.jpg",
            headers=auth_headers,
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "https://storage.supabase.co/signed-url-here"
