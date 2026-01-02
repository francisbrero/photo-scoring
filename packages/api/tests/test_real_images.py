"""Tests for loading real images from test_photos folder."""

import base64
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from .conftest import FAKE_SERVICE_JWT

# Path to test photos
TEST_PHOTOS_DIR = Path(__file__).parent.parent.parent.parent / "test_photos"


class TestRealImages:
    """Tests for loading real images from test_photos folder."""

    def test_jpeg_image(self, monkeypatch):
        """Test loading a real JPEG image."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        jpeg_path = TEST_PHOTOS_DIR / "IMG_2773.JPG"
        if not jpeg_path.exists():
            pytest.skip("Test JPEG not found")

        from api.services.openrouter import OpenRouterService

        service = OpenRouterService()
        image_data = jpeg_path.read_bytes()

        # Check JPEG signature
        assert image_data[:2] == b"\xff\xd8", "Not a valid JPEG file"

        # Load and encode
        b64_data, media_type = service._load_and_encode_image(image_data)
        assert media_type == "image/jpeg"
        assert len(b64_data) > 0

        # Verify we can decode it back
        decoded = base64.b64decode(b64_data)
        img = Image.open(BytesIO(decoded))
        assert img.format == "JPEG"

    def test_heic_image(self, monkeypatch):
        """Test loading a real HEIC image (converted to JPEG)."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        heic_path = TEST_PHOTOS_DIR / "IMG_1305.HEIC"
        if not heic_path.exists():
            pytest.skip("Test HEIC not found")

        from api.services.openrouter import OpenRouterService

        service = OpenRouterService()
        image_data = heic_path.read_bytes()

        # Load and encode (should convert HEIC to JPEG)
        b64_data, media_type = service._load_and_encode_image(image_data)
        assert media_type == "image/jpeg"
        assert len(b64_data) > 0

        # Verify we can decode it back
        decoded = base64.b64decode(b64_data)
        img = Image.open(BytesIO(decoded))
        assert img.format == "JPEG"
