"""Shared image preprocessing utilities."""

import base64
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

MAX_IMAGE_DIMENSION = 2048

# Register HEIC/HEIF support
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    pass


def load_and_preprocess_image(
    image_path: Path, max_dimension: int = MAX_IMAGE_DIMENSION
) -> Image.Image:
    """Load image, apply EXIF transpose, convert to RGB, resize if needed."""
    img = Image.open(image_path)
    img = ImageOps.exif_transpose(img)

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    if max(img.size) > max_dimension:
        ratio = max_dimension / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    return img


def encode_image_base64(image: Image.Image, quality: int = 85) -> tuple[str, str]:
    """Encode PIL Image to base64 JPEG.

    Returns:
        Tuple of (base64_data, media_type).
    """
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return base64_data, "image/jpeg"
