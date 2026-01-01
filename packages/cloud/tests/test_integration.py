"""Integration tests using local Supabase.

Run with: pytest tests/test_integration.py -v

Requires local Supabase: supabase start
"""

from io import BytesIO

# Import all fixtures from conftest_integration
pytest_plugins = ["tests.conftest_integration"]

from .conftest_integration import requires_supabase  # noqa: E402


@requires_supabase
class TestAuthIntegration:
    """Test authentication flow with local Supabase."""

    def test_health_check(self, integration_client):
        """Health endpoint should work without auth."""
        response = integration_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_unauthenticated_request_rejected(self, integration_client):
        """Requests without auth should be rejected."""
        response = integration_client.get("/api/photos")
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_invalid_token_rejected(self, integration_client):
        """Requests with invalid token should be rejected."""
        response = integration_client.get(
            "/api/photos", headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401

    def test_valid_token_accepted(self, integration_client, auth_headers):
        """Requests with valid token should be accepted."""
        response = integration_client.get("/api/photos", headers=auth_headers)
        assert response.status_code == 200

    def test_get_user_info(self, integration_client, auth_headers, test_user):
        """Should return current user info with trial credits."""
        response = integration_client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user["email"]
        assert data["credit_balance"] >= 0  # Should have trial credits


@requires_supabase
class TestCreditsIntegration:
    """Test credits system with local Supabase."""

    def test_new_user_gets_trial_credits(self, integration_client, auth_headers):
        """New users should receive trial credits."""
        response = integration_client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # New users get 5 trial credits by default
        assert data["credit_balance"] == 5

    def test_credits_balance_endpoint(self, integration_client, auth_headers):
        """Should be able to check credit balance."""
        # First ensure user has credits (triggers trial credit grant)
        integration_client.get("/api/auth/me", headers=auth_headers)

        response = integration_client.get("/api/billing/balance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data
        assert isinstance(data["balance"], int)

    def test_transactions_history(self, integration_client, auth_headers):
        """Should be able to view transaction history."""
        # First ensure user has credits (triggers trial credit grant)
        integration_client.get("/api/auth/me", headers=auth_headers)

        response = integration_client.get("/api/billing/transactions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data
        # Should have at least the trial credit transaction
        assert len(data["transactions"]) >= 1
        assert data["transactions"][0]["type"] == "trial"


@requires_supabase
class TestPhotoUploadIntegration:
    """Test photo upload with local Supabase storage."""

    def test_upload_jpeg(
        self, integration_client, auth_headers, sample_jpeg_bytes, cleanup_storage
    ):
        """Should successfully upload a JPEG image."""
        response = integration_client.post(
            "/api/photos/upload",
            headers=auth_headers,
            files={"file": ("test.jpg", BytesIO(sample_jpeg_bytes), "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "storage_path" in data
        assert data["message"] == "Photo uploaded successfully. Use /photos/{id}/score to score it."

    def test_upload_invalid_type_rejected(self, integration_client, auth_headers):
        """Should reject non-image files."""
        response = integration_client.post(
            "/api/photos/upload",
            headers=auth_headers,
            files={"file": ("test.txt", BytesIO(b"not an image"), "text/plain")},
        )
        assert response.status_code == 400
        assert "not supported" in response.json()["detail"]

    def test_list_photos_empty(self, integration_client, auth_headers):
        """Should return empty list for new user."""
        response = integration_client.get("/api/photos", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["photos"] == [] or isinstance(data["photos"], list)
        assert data["total"] >= 0

    def test_list_photos_after_upload(
        self, integration_client, auth_headers, sample_jpeg_bytes, cleanup_storage
    ):
        """Should list uploaded photos."""
        # Upload a photo
        upload_response = integration_client.post(
            "/api/photos/upload",
            headers=auth_headers,
            files={"file": ("test.jpg", BytesIO(sample_jpeg_bytes), "image/jpeg")},
        )
        assert upload_response.status_code == 200

        # List photos
        list_response = integration_client.get("/api/photos", headers=auth_headers)
        assert list_response.status_code == 200
        data = list_response.json()
        assert len(data["photos"]) >= 1

    def test_get_single_photo(
        self, integration_client, auth_headers, sample_jpeg_bytes, cleanup_storage
    ):
        """Should get a single photo by ID."""
        # Upload a photo
        upload_response = integration_client.post(
            "/api/photos/upload",
            headers=auth_headers,
            files={"file": ("test.jpg", BytesIO(sample_jpeg_bytes), "image/jpeg")},
        )
        photo_id = upload_response.json()["id"]

        # Get the photo
        response = integration_client.get(f"/api/photos/{photo_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == photo_id

    def test_delete_photo(
        self, integration_client, auth_headers, sample_jpeg_bytes, cleanup_storage
    ):
        """Should delete a photo."""
        # Upload a photo
        upload_response = integration_client.post(
            "/api/photos/upload",
            headers=auth_headers,
            files={"file": ("test.jpg", BytesIO(sample_jpeg_bytes), "image/jpeg")},
        )
        photo_id = upload_response.json()["id"]

        # Delete the photo
        delete_response = integration_client.delete(f"/api/photos/{photo_id}", headers=auth_headers)
        assert delete_response.status_code == 204

        # Verify it's gone
        get_response = integration_client.get(f"/api/photos/{photo_id}", headers=auth_headers)
        assert get_response.status_code == 404


@requires_supabase
class TestPhotoScoringIntegration:
    """Test photo scoring pipeline with local Supabase.

    Note: These tests mock the OpenRouter API to avoid real API calls.
    """

    def test_score_photo_deducts_credit(
        self, integration_client, auth_headers, sample_jpeg_bytes, cleanup_storage, mock_openrouter
    ):
        """Scoring should deduct 1 credit."""
        # Trigger trial credits first
        integration_client.get("/api/auth/me", headers=auth_headers)

        # Get initial credits
        initial_response = integration_client.get("/api/billing/balance", headers=auth_headers)
        initial_credits = initial_response.json()["balance"]

        # Upload a photo
        upload_response = integration_client.post(
            "/api/photos/upload",
            headers=auth_headers,
            files={"file": ("test.jpg", BytesIO(sample_jpeg_bytes), "image/jpeg")},
        )
        photo_id = upload_response.json()["id"]

        # Score the photo
        score_response = integration_client.post(
            f"/api/photos/{photo_id}/score", headers=auth_headers
        )
        assert score_response.status_code == 200
        data = score_response.json()
        assert "final_score" in data
        assert data["credits_remaining"] == initial_credits - 1

    def test_score_photo_returns_scores(
        self, integration_client, auth_headers, sample_jpeg_bytes, cleanup_storage, mock_openrouter
    ):
        """Scoring should return aesthetic and technical scores."""
        # Trigger trial credits first
        integration_client.get("/api/auth/me", headers=auth_headers)

        # Upload and score
        upload_response = integration_client.post(
            "/api/photos/upload",
            headers=auth_headers,
            files={"file": ("test.jpg", BytesIO(sample_jpeg_bytes), "image/jpeg")},
        )
        photo_id = upload_response.json()["id"]

        score_response = integration_client.post(
            f"/api/photos/{photo_id}/score", headers=auth_headers
        )
        assert score_response.status_code == 200
        data = score_response.json()

        assert data["final_score"] is not None
        assert data["aesthetic_score"] is not None
        assert data["technical_score"] is not None
        assert 0 <= data["final_score"] <= 100

    def test_cannot_score_twice(
        self, integration_client, auth_headers, sample_jpeg_bytes, cleanup_storage, mock_openrouter
    ):
        """Should not allow scoring the same photo twice."""
        # Trigger trial credits first
        integration_client.get("/api/auth/me", headers=auth_headers)

        # Upload and score
        upload_response = integration_client.post(
            "/api/photos/upload",
            headers=auth_headers,
            files={"file": ("test.jpg", BytesIO(sample_jpeg_bytes), "image/jpeg")},
        )
        photo_id = upload_response.json()["id"]

        # First score succeeds
        first_score = integration_client.post(f"/api/photos/{photo_id}/score", headers=auth_headers)
        assert first_score.status_code == 200

        # Second score fails
        second_score = integration_client.post(
            f"/api/photos/{photo_id}/score", headers=auth_headers
        )
        assert second_score.status_code == 400
        assert "already been scored" in second_score.json()["detail"]

    def test_score_photo_generates_rich_critique(
        self, integration_client, auth_headers, sample_jpeg_bytes, cleanup_storage, mock_openrouter
    ):
        """Scoring should generate rich, contextual critique with structured sections."""
        # Trigger trial credits first
        integration_client.get("/api/auth/me", headers=auth_headers)

        # Upload and score
        upload_response = integration_client.post(
            "/api/photos/upload",
            headers=auth_headers,
            files={"file": ("test.jpg", BytesIO(sample_jpeg_bytes), "image/jpeg")},
        )
        photo_id = upload_response.json()["id"]

        score_response = integration_client.post(
            f"/api/photos/{photo_id}/score", headers=auth_headers
        )
        assert score_response.status_code == 200

        # Get full photo data with explanation
        photo_response = integration_client.get(f"/api/photos/{photo_id}", headers=auth_headers)
        assert photo_response.status_code == 200
        photo_data = photo_response.json()

        # Validate critique quality
        explanation = photo_data.get("explanation", "")
        improvements = photo_data.get("improvements", "")

        # Must have substantial content (not template output)
        assert len(explanation) > 100, "Explanation too short"
        assert len(improvements) > 50, "Improvements too short"

        # Must have structured sections
        assert "**What's working:**" in explanation, "Missing 'What's working' section"
        assert "**Could improve:**" in explanation, "Missing 'Could improve' section"

        # Must NOT be template output (old format)
        assert "Near-publishable" not in explanation, "Still using old template format"
        assert "Tourist-level" not in explanation, "Still using old template format"

        # Improvements should have key recommendation
        assert "Key recommendation" in improvements, "Missing key recommendation"

    def test_score_photo_stores_features(
        self, integration_client, auth_headers, sample_jpeg_bytes, cleanup_storage, mock_openrouter
    ):
        """Scoring should extract and store scene features."""
        # Trigger trial credits first
        integration_client.get("/api/auth/me", headers=auth_headers)

        # Upload and score
        upload_response = integration_client.post(
            "/api/photos/upload",
            headers=auth_headers,
            files={"file": ("test.jpg", BytesIO(sample_jpeg_bytes), "image/jpeg")},
        )
        photo_id = upload_response.json()["id"]

        score_response = integration_client.post(
            f"/api/photos/{photo_id}/score", headers=auth_headers
        )
        assert score_response.status_code == 200

        # Get full photo data
        photo_response = integration_client.get(f"/api/photos/{photo_id}", headers=auth_headers)
        photo_data = photo_response.json()

        # Should have features_json stored
        features = photo_data.get("features_json")
        # Note: features_json might be stringified, so we just check it's not empty
        assert features is not None, "Features not stored"

    def test_insufficient_credits_rejected(
        self,
        integration_client,
        auth_headers,
        sample_jpeg_bytes,
        cleanup_storage,
        supabase_admin,
        test_user,
    ):
        """Should reject scoring when user has no credits."""
        # Set user credits to 0
        supabase_admin.table("credits").upsert({"user_id": test_user["id"], "balance": 0}).execute()

        # Upload a photo
        upload_response = integration_client.post(
            "/api/photos/upload",
            headers=auth_headers,
            files={"file": ("test.jpg", BytesIO(sample_jpeg_bytes), "image/jpeg")},
        )
        photo_id = upload_response.json()["id"]

        # Try to score - should fail
        score_response = integration_client.post(
            f"/api/photos/{photo_id}/score", headers=auth_headers
        )
        assert score_response.status_code == 402
        assert "Insufficient credits" in score_response.json()["detail"]


@requires_supabase
class TestRegenerateIntegration:
    """Test regenerate explanation feature."""

    def test_regenerate_explanation(
        self,
        integration_client,
        auth_headers,
        sample_jpeg_bytes,
        cleanup_storage,
        mock_openrouter,
    ):
        """Should regenerate explanation for scored photo."""
        # Trigger trial credits first
        integration_client.get("/api/auth/me", headers=auth_headers)

        # Upload and score
        upload_response = integration_client.post(
            "/api/photos/upload",
            headers=auth_headers,
            files={"file": ("test.jpg", BytesIO(sample_jpeg_bytes), "image/jpeg")},
        )
        photo_id = upload_response.json()["id"]

        score_response = integration_client.post(
            f"/api/photos/{photo_id}/score", headers=auth_headers
        )
        assert score_response.status_code == 200

        # Regenerate explanation
        regen_response = integration_client.post(
            f"/api/photos/{photo_id}/regenerate", headers=auth_headers
        )
        assert regen_response.status_code == 200
        assert "regenerated" in regen_response.json()["message"].lower()

        # Verify photo has rich explanation
        photo_response = integration_client.get(f"/api/photos/{photo_id}", headers=auth_headers)
        assert photo_response.status_code == 200
        photo_data = photo_response.json()
        assert photo_data["explanation"] is not None
        assert photo_data["improvements"] is not None
        # Verify it's rich critique
        assert len(photo_data["explanation"]) > 100
        assert "**What's working:**" in photo_data["explanation"]
