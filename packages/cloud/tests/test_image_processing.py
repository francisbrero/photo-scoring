"""Tests for image processing in OpenRouterService."""

import base64
from io import BytesIO

import pytest
from PIL import Image

from .conftest import FAKE_SERVICE_JWT


def create_test_jpeg() -> bytes:
    """Create a valid JPEG image for testing."""
    img = Image.new("RGB", (100, 100), color="red")
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def create_test_png() -> bytes:
    """Create a valid PNG image for testing."""
    img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 255))
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


class TestImageProcessing:
    """Tests for image loading and encoding."""

    def test_load_jpeg(self, monkeypatch):
        """Test loading a JPEG image."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        from api.services.openrouter import OpenRouterService

        service = OpenRouterService()
        image_data = create_test_jpeg()

        # Verify we can load and encode the image
        b64_data, media_type = service._load_and_encode_image(image_data)

        assert media_type == "image/jpeg"
        assert len(b64_data) > 0

        # Verify we can decode it back
        decoded = base64.b64decode(b64_data)
        img = Image.open(BytesIO(decoded))
        assert img.format == "JPEG"

    def test_load_png(self, monkeypatch):
        """Test loading a PNG image (should convert to JPEG)."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        from api.services.openrouter import OpenRouterService

        service = OpenRouterService()
        image_data = create_test_png()

        # Verify we can load and encode the image
        b64_data, media_type = service._load_and_encode_image(image_data)

        assert media_type == "image/jpeg"  # Converted to JPEG
        assert len(b64_data) > 0

    def test_load_large_image(self, monkeypatch):
        """Test loading a large image (should resize)."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        from api.services.openrouter import MAX_IMAGE_DIMENSION, OpenRouterService

        service = OpenRouterService()

        # Create a large image (3000x2000)
        img = Image.new("RGB", (3000, 2000), color="blue")
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        image_data = buffer.getvalue()

        # Verify we can load and encode the image
        b64_data, media_type = service._load_and_encode_image(image_data)

        # Verify it was resized
        decoded = base64.b64decode(b64_data)
        result_img = Image.open(BytesIO(decoded))
        assert max(result_img.size) <= MAX_IMAGE_DIMENSION

    def test_load_empty_data(self, monkeypatch):
        """Test loading empty data raises error."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        from api.services.openrouter import InferenceError, OpenRouterService

        service = OpenRouterService()

        with pytest.raises(InferenceError, match="Empty image data"):
            service._load_and_encode_image(b"")

    def test_load_invalid_data(self, monkeypatch):
        """Test loading invalid data raises error."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        from api.services.openrouter import InferenceError, OpenRouterService

        service = OpenRouterService()

        with pytest.raises(InferenceError, match="Cannot open image"):
            service._load_and_encode_image(b"not an image")

    def test_decode_base64_image(self, monkeypatch):
        """Test base64 decoding."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        from api.services.openrouter import OpenRouterService

        image_data = create_test_jpeg()
        b64_data = base64.b64encode(image_data).decode("utf-8")

        # Test raw base64
        decoded = OpenRouterService.decode_base64_image(b64_data)
        assert decoded == image_data

        # Test data URL format
        data_url = f"data:image/jpeg;base64,{b64_data}"
        decoded = OpenRouterService.decode_base64_image(data_url)
        assert decoded == image_data

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

        assert "aesthetic_score" in scores
        assert "technical_score" in scores
        assert "final_score" in scores
        assert 0 <= scores["aesthetic_score"] <= 1
        assert 0 <= scores["technical_score"] <= 1
        assert 0 <= scores["final_score"] <= 100


class TestBase64Handling:
    """Tests for base64 encoding edge cases."""

    def test_heic_style_data(self, monkeypatch):
        """Test handling of image data that might come from HEIC conversion."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        from api.services.openrouter import OpenRouterService

        service = OpenRouterService()

        # Create a grayscale image (L mode)
        img = Image.new("L", (100, 100), color=128)
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        image_data = buffer.getvalue()

        # Should handle grayscale
        b64_data, media_type = service._load_and_encode_image(image_data)
        assert len(b64_data) > 0

    def test_rgba_image(self, monkeypatch):
        """Test handling of RGBA images (with alpha channel)."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        from api.services.openrouter import OpenRouterService

        service = OpenRouterService()

        # Create RGBA image
        img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        image_data = buffer.getvalue()

        # Should convert RGBA to RGB
        b64_data, media_type = service._load_and_encode_image(image_data)
        assert media_type == "image/jpeg"

        # Verify it's valid
        decoded = base64.b64decode(b64_data)
        result_img = Image.open(BytesIO(decoded))
        assert result_img.mode == "RGB"
