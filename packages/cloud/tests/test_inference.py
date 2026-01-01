"""Tests for inference router."""

import base64

from .conftest import FAKE_SERVICE_JWT

# Sample 1x1 white pixel JPEG for testing
TINY_JPEG = base64.b64encode(
    bytes.fromhex(
        "ffd8ffe000104a46494600010100000100010000"
        "ffdb004300080606070605080707070909080a0c"
        "140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20"
        "242e2720222c231c1c2837292c30313434341f27"
        "393d38323c2e333432ffdb0043010909090c0b0c"
        "180d0d1832211c213232323232323232323232"
        "32323232323232323232323232323232323232"
        "3232323232323232323232323232ffc00011"
        "080001000103012200021101031101ffc4001f"
        "0000010501010101010100000000000000000102"
        "030405060708090a0bffc400b51000020103"
        "0302040305050404000001017d010203000411"
        "05122131410613516107227114328191a10823"
        "42b1c11552d1f02433627282090a161718191a"
        "25262728292a3435363738393a434445464748"
        "494a535455565758595a636465666768696a"
        "737475767778797a838485868788898a929394"
        "9596979899ffda000c03010002110311003f00"
        "f9fe2800a002800a002800a002800a0028"
    )
).decode()


def test_analyze_requires_auth(client):
    """Test that inference/analyze requires authentication."""
    response = client.post(
        "/api/inference/analyze",
        json={"image_data": TINY_JPEG},
    )
    assert response.status_code == 401


def test_metadata_requires_auth(client):
    """Test that inference/metadata requires authentication."""
    response = client.post(
        "/api/inference/metadata",
        json={"image_data": TINY_JPEG},
    )
    assert response.status_code == 401


def test_analyze_invalid_base64(client, auth_token):
    """Test that invalid base64 returns 400."""
    response = client.post(
        "/api/inference/analyze",
        json={"image_data": "not-valid-base64!!!"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    # Should fail at base64 validation with 400
    assert response.status_code == 400


class TestOpenRouterService:
    """Tests for OpenRouterService."""

    def test_compute_scores(self, monkeypatch):
        """Test score computation from attributes."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        from api.services.openrouter import OpenRouterService

        attributes = {
            "composition": 0.7,
            "subject_strength": 0.6,
            "visual_appeal": 0.8,
            "sharpness": 0.5,
            "exposure_balance": 0.7,
            "noise_level": 0.6,
        }

        scores = OpenRouterService.compute_scores(attributes)

        # Check aesthetic score (0.7*0.4 + 0.6*0.35 + 0.8*0.25 = 0.28 + 0.21 + 0.2 = 0.69)
        assert abs(scores["aesthetic_score"] - 0.69) < 0.01

        # Check technical score (0.5*0.4 + 0.7*0.35 + 0.6*0.25 = 0.2 + 0.245 + 0.15 = 0.595)
        assert abs(scores["technical_score"] - 0.595) < 0.01

        # Check final score ((0.69*0.6 + 0.595*0.4) * 100 = 65.2)
        assert abs(scores["final_score"] - 65.2) < 0.5

    def test_compute_scores_with_sharpness_penalty(self, monkeypatch):
        """Test that low sharpness applies penalty."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        from api.services.openrouter import OpenRouterService

        # Very low sharpness should apply penalty
        attributes = {
            "composition": 0.7,
            "subject_strength": 0.6,
            "visual_appeal": 0.8,
            "sharpness": 0.1,  # Low sharpness
            "exposure_balance": 0.7,
            "noise_level": 0.6,
        }

        scores = OpenRouterService.compute_scores(attributes)

        # Final score should be penalized
        # Without penalty: ~63
        # With 50% sharpness penalty at 0.1: 50% of 0.5 = 25% penalty
        assert scores["final_score"] < 60

    def test_compute_image_hash(self, monkeypatch):
        """Test image hash computation."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        from api.services.openrouter import OpenRouterService

        data = b"test image data"
        hash1 = OpenRouterService.compute_image_hash(data)
        hash2 = OpenRouterService.compute_image_hash(data)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex

    def test_decode_base64_image(self, monkeypatch):
        """Test base64 decoding."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        from api.services.openrouter import OpenRouterService

        original = b"test data"
        encoded = base64.b64encode(original).decode()

        decoded = OpenRouterService.decode_base64_image(encoded)
        assert decoded == original

    def test_decode_base64_with_data_url(self, monkeypatch):
        """Test base64 decoding with data URL prefix."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        from api.services.openrouter import OpenRouterService

        original = b"test data"
        encoded = f"data:image/jpeg;base64,{base64.b64encode(original).decode()}"

        decoded = OpenRouterService.decode_base64_image(encoded)
        assert decoded == original


class TestCritiqueFormatting:
    """Tests for critique formatting methods."""

    def test_format_explanation(self, monkeypatch):
        """Test that format_explanation produces structured output."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        from api.services.openrouter import OpenRouterService

        critique = {
            "summary": "This is a well-composed landscape shot with good lighting.",
            "working_well": [
                "Strong composition with rule of thirds placement.",
                "Excellent golden hour lighting adds warmth.",
            ],
            "could_improve": [
                "Consider adding foreground interest.",
                "The horizon could be straighter.",
            ],
            "key_recommendation": "Return at sunset for more dramatic light.",
        }

        explanation = OpenRouterService.format_explanation(critique)

        assert "This is a well-composed landscape shot" in explanation
        assert "**What's working:**" in explanation
        assert "Strong composition" in explanation
        assert "**Could improve:**" in explanation
        assert "foreground interest" in explanation

    def test_format_explanation_empty_critique(self, monkeypatch):
        """Test that format_explanation handles empty critique gracefully."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        from api.services.openrouter import OpenRouterService

        critique = {}
        explanation = OpenRouterService.format_explanation(critique)

        assert explanation == "Unable to generate critique."

    def test_format_improvements(self, monkeypatch):
        """Test that format_improvements extracts key recommendation."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        from api.services.openrouter import OpenRouterService

        critique = {
            "could_improve": [
                "Add foreground interest.",
                "Straighten the horizon.",
            ],
            "key_recommendation": "Return at sunset for dramatic light.",
        }

        improvements = OpenRouterService.format_improvements(critique)

        assert "Add foreground interest." in improvements
        assert "Straighten the horizon." in improvements
        assert "**Key recommendation:**" in improvements
        assert "sunset" in improvements

    def test_format_improvements_empty(self, monkeypatch):
        """Test that format_improvements handles empty critique."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        from api.services.openrouter import OpenRouterService

        critique = {}
        improvements = OpenRouterService.format_improvements(critique)

        assert improvements == "No specific improvements identified."


class TestRateLimiting:
    """Tests for rate limiting."""

    def test_rate_limit_check(self, monkeypatch):
        """Test rate limit checking."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        from api.routers.inference import (
            RATE_LIMIT_REQUESTS,
            _rate_limits,
            check_rate_limit,
        )

        user_id = "test-user-rate-limit"
        _rate_limits.pop(user_id, None)  # Clear any existing

        # Should allow up to RATE_LIMIT_REQUESTS
        for i in range(RATE_LIMIT_REQUESTS):
            assert check_rate_limit(user_id) is True

        # Should deny the next one
        assert check_rate_limit(user_id) is False

        # Clean up
        _rate_limits.pop(user_id, None)
