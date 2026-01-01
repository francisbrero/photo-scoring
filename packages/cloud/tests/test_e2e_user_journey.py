"""End-to-end test for complete user journey.

This test simulates a real user:
1. Signs up for an account
2. Receives trial credits
3. Uploads a photo
4. Scores the photo
5. Views the results
6. Regenerates the explanation

Run with: pytest tests/test_e2e_user_journey.py -v
"""

import os
from io import BytesIO

import pytest

# Import all fixtures from conftest_integration
pytest_plugins = ["tests.conftest_integration"]

from .conftest_integration import (  # noqa: E402
    LOCAL_JWT_SECRET,
    LOCAL_SUPABASE_SERVICE_KEY,
    LOCAL_SUPABASE_URL,
    requires_supabase,
)


@requires_supabase
class TestFullUserJourney:
    """Complete end-to-end test of user journey."""

    @pytest.fixture
    def e2e_client(self, monkeypatch):
        """Create test client for e2e tests."""
        from api.config import get_settings

        get_settings.cache_clear()

        monkeypatch.setenv("SUPABASE_URL", LOCAL_SUPABASE_URL)
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", LOCAL_SUPABASE_SERVICE_KEY)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", LOCAL_JWT_SECRET)
        monkeypatch.setenv("OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY", "test-key"))
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
        monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_fake")

        from fastapi.testclient import TestClient

        from api.main import create_app

        app = create_app()
        return TestClient(app)

    @pytest.fixture
    def mock_ai_service(self, monkeypatch):
        """Mock AI service to avoid real API calls."""
        from api.services import openrouter

        async def mock_analyze_image(self, image_data, image_hash):
            return {
                "composition": 0.75,
                "subject_strength": 0.82,
                "visual_appeal": 0.68,
                "sharpness": 0.91,
                "exposure_balance": 0.85,
                "noise_level": 0.12,
            }

        async def mock_analyze_metadata(self, image_data, image_hash):
            return {
                "description": "A beautiful landscape photograph",
                "location_name": "Mountain View",
                "location_country": "USA",
            }

        monkeypatch.setattr(openrouter.OpenRouterService, "analyze_image", mock_analyze_image)
        monkeypatch.setattr(
            openrouter.OpenRouterService, "analyze_image_metadata", mock_analyze_metadata
        )

    @pytest.fixture
    def test_image(self) -> bytes:
        """Load a real test image or create a valid JPEG."""
        # Try to load real test image first
        test_image_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "test_photos", "IMG_2773.JPG"
        )
        if os.path.exists(test_image_path):
            with open(test_image_path, "rb") as f:
                return f.read()

        # Fallback to minimal valid JPEG
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
                0xD3,
                0x28,
                0xA8,
                0x00,
                0xFF,
                0xD9,
            ]
        )

    def test_complete_user_journey(self, e2e_client, mock_ai_service, test_image, supabase_admin):
        """
        Test the complete user journey from signup to viewing scored photos.

        This test covers:
        1. New user receives trial credits on first API call
        2. User can upload a photo
        3. User can score the photo (deducts credit)
        4. User can view the scored photo with all details
        5. User can regenerate explanation
        6. Photo response includes all expected fields
        """
        import uuid

        from jose import jwt

        # Create a test user
        email = f"e2e_test_{uuid.uuid4().hex[:8]}@example.com"
        user_response = supabase_admin.auth.admin.create_user(
            {
                "email": email,
                "password": "testpassword123",
                "email_confirm": True,
            }
        )
        user_id = user_response.user.id

        # Create auth token
        token = jwt.encode(
            {
                "sub": user_id,
                "email": email,
                "role": "authenticated",
                "aud": "authenticated",
                "iat": 1704067200,
                "exp": 1988150400,
            },
            LOCAL_JWT_SECRET,
            algorithm="HS256",
        )
        auth_headers = {"Authorization": f"Bearer {token}"}

        try:
            # ============================================
            # Step 1: Check initial state (triggers trial credits)
            # ============================================
            me_response = e2e_client.get("/api/auth/me", headers=auth_headers)
            assert me_response.status_code == 200, f"Failed to get user info: {me_response.json()}"
            user_info = me_response.json()
            assert user_info["email"] == email
            assert user_info["credit_balance"] == 5, "New user should have 5 trial credits"

            # ============================================
            # Step 2: Upload a photo
            # ============================================
            upload_response = e2e_client.post(
                "/api/photos/upload",
                headers=auth_headers,
                files={"file": ("landscape.jpg", BytesIO(test_image), "image/jpeg")},
            )
            assert upload_response.status_code == 200, f"Upload failed: {upload_response.json()}"
            upload_data = upload_response.json()
            photo_id = upload_data["id"]
            assert photo_id is not None
            assert "storage_path" in upload_data

            # ============================================
            # Step 3: Score the photo
            # ============================================
            score_response = e2e_client.post(f"/api/photos/{photo_id}/score", headers=auth_headers)
            assert score_response.status_code == 200, f"Scoring failed: {score_response.json()}"
            score_data = score_response.json()

            # Verify scores are present
            assert score_data["final_score"] is not None
            assert 0 <= score_data["final_score"] <= 100
            assert score_data["aesthetic_score"] is not None
            assert score_data["technical_score"] is not None
            assert score_data["credits_remaining"] == 4  # 5 - 1 = 4

            # ============================================
            # Step 4: View the scored photo
            # ============================================
            photo_response = e2e_client.get(f"/api/photos/{photo_id}", headers=auth_headers)
            assert photo_response.status_code == 200, f"Get photo failed: {photo_response.json()}"
            photo_data = photo_response.json()

            # Verify all expected fields are present
            assert photo_data["id"] == photo_id
            assert photo_data["final_score"] is not None
            assert photo_data["aesthetic_score"] is not None
            assert photo_data["technical_score"] is not None
            assert photo_data["image_url"] is not None  # Signed URL for display
            assert photo_data["explanation"] is not None
            assert photo_data["improvements"] is not None

            # Verify individual attribute scores
            assert photo_data["composition"] is not None
            assert photo_data["subject_strength"] is not None
            assert photo_data["visual_appeal"] is not None
            assert photo_data["sharpness"] is not None
            assert photo_data["exposure"] is not None
            assert photo_data["noise_level"] is not None

            # ============================================
            # Step 5: Regenerate explanation
            # ============================================
            regen_response = e2e_client.post(
                f"/api/photos/{photo_id}/regenerate", headers=auth_headers
            )
            assert regen_response.status_code == 200, f"Regenerate failed: {regen_response.json()}"

            # Verify explanation was updated
            updated_photo = e2e_client.get(f"/api/photos/{photo_id}", headers=auth_headers).json()
            assert updated_photo["explanation"] is not None
            assert updated_photo["improvements"] is not None

            # ============================================
            # Step 6: List all photos
            # ============================================
            list_response = e2e_client.get("/api/photos", headers=auth_headers)
            assert list_response.status_code == 200
            list_data = list_response.json()
            assert list_data["total"] >= 1
            assert len(list_data["photos"]) >= 1
            assert any(p["id"] == photo_id for p in list_data["photos"])

            # ============================================
            # Step 7: Verify credit was deducted
            # ============================================
            balance_response = e2e_client.get("/api/billing/balance", headers=auth_headers)
            assert balance_response.status_code == 200
            assert balance_response.json()["balance"] == 4

            # ============================================
            # Step 8: Verify transaction history
            # ============================================
            tx_response = e2e_client.get("/api/billing/transactions", headers=auth_headers)
            assert tx_response.status_code == 200
            transactions = tx_response.json()["transactions"]
            assert len(transactions) >= 2  # trial + inference

            # Check transaction types
            tx_types = [tx["type"] for tx in transactions]
            assert "trial" in tx_types
            assert "inference" in tx_types

        finally:
            # Cleanup: delete user and their data
            try:
                # Delete photos from storage
                photos = (
                    supabase_admin.table("scored_photos")
                    .select("storage_path")
                    .eq("user_id", user_id)
                    .execute()
                )
                if photos.data:
                    paths = [p["storage_path"] for p in photos.data]
                    supabase_admin.storage.from_("photos").remove(paths)

                # Delete user (cascades to all related tables)
                supabase_admin.auth.admin.delete_user(user_id)
            except Exception:
                pass

    def test_cannot_score_without_credits(self, e2e_client, test_image, supabase_admin):
        """Test that scoring fails when user has no credits."""
        import uuid

        from jose import jwt

        # Create a test user
        email = f"e2e_nocredits_{uuid.uuid4().hex[:8]}@example.com"
        user_response = supabase_admin.auth.admin.create_user(
            {
                "email": email,
                "password": "testpassword123",
                "email_confirm": True,
            }
        )
        user_id = user_response.user.id

        # Create auth token
        token = jwt.encode(
            {
                "sub": user_id,
                "email": email,
                "role": "authenticated",
                "aud": "authenticated",
                "iat": 1704067200,
                "exp": 1988150400,
            },
            LOCAL_JWT_SECRET,
            algorithm="HS256",
        )
        auth_headers = {"Authorization": f"Bearer {token}"}

        try:
            # Trigger trial credits first
            e2e_client.get("/api/auth/me", headers=auth_headers)

            # Set credits to 0
            supabase_admin.table("credits").update({"balance": 0}).eq("user_id", user_id).execute()

            # Upload a photo
            upload_response = e2e_client.post(
                "/api/photos/upload",
                headers=auth_headers,
                files={"file": ("test.jpg", BytesIO(test_image), "image/jpeg")},
            )
            photo_id = upload_response.json()["id"]

            # Try to score - should fail
            score_response = e2e_client.post(f"/api/photos/{photo_id}/score", headers=auth_headers)
            assert score_response.status_code == 402
            assert "Insufficient credits" in score_response.json()["detail"]

        finally:
            try:
                supabase_admin.auth.admin.delete_user(user_id)
            except Exception:
                pass
