"""Tests for loading real images from test_photos folder."""

import base64
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from .conftest import FAKE_SERVICE_JWT

# Path to test photos
TEST_PHOTOS_DIR = Path(__file__).parent.parent.parent.parent / "test_photos"


def get_test_images():
    """Get list of test images if directory exists."""
    if not TEST_PHOTOS_DIR.exists():
        return []
    return list(TEST_PHOTOS_DIR.glob("*"))


class TestRealImages:
    """Tests for loading real images from test_photos folder."""

    @pytest.mark.parametrize("image_path", get_test_images(), ids=lambda p: p.name)
    def test_load_real_image(self, monkeypatch, image_path):
        """Test loading real images from test_photos folder."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", FAKE_SERVICE_JWT)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        from api.services.openrouter import OpenRouterService

        service = OpenRouterService()

        # Read the image file
        image_data = image_path.read_bytes()
        print(f"\nTesting: {image_path.name}")
        print(f"  File size: {len(image_data)} bytes")
        print(f"  First 20 bytes: {image_data[:20].hex()}")

        # Try to load and encode
        b64_data, media_type = service._load_and_encode_image(image_data)

        assert media_type == "image/jpeg"
        assert len(b64_data) > 0

        # Verify we can decode it back
        decoded = base64.b64decode(b64_data)
        img = Image.open(BytesIO(decoded))
        assert img.format == "JPEG"
        print(f"  Output size: {img.size}")
        print(f"  Output mode: {img.mode}")

    def test_jpeg_image(self, monkeypatch):
        """Test loading a specific JPEG image."""
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

        print(f"\nJPEG test: {jpeg_path.name}")
        print(f"  File size: {len(image_data)} bytes")
        print(f"  First 20 bytes hex: {image_data[:20].hex()}")

        # Check JPEG signature
        assert image_data[:2] == b"\xff\xd8", "Not a valid JPEG file"

        b64_data, media_type = service._load_and_encode_image(image_data)
        assert media_type == "image/jpeg"

    def test_heic_image(self, monkeypatch):
        """Test loading a specific HEIC image."""
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

        print(f"\nHEIC test: {heic_path.name}")
        print(f"  File size: {len(image_data)} bytes")
        print(f"  First 20 bytes hex: {image_data[:20].hex()}")

        b64_data, media_type = service._load_and_encode_image(image_data)
        assert media_type == "image/jpeg"  # Should convert to JPEG
