"""Image discovery and file hashing."""

import hashlib
from pathlib import Path

from photo_score.storage.models import ImageRecord

DEFAULT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}


def compute_image_id(file_path: Path) -> str:
    """Compute SHA256 hash of file contents."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def discover_images(
    root_path: Path,
    extensions: set[str] | None = None,
) -> list[ImageRecord]:
    """Recursively discover all images under root_path.

    Args:
        root_path: Root directory to scan.
        extensions: Set of allowed extensions (with leading dot).
                   Defaults to jpg, jpeg, png, heic, heif.

    Returns:
        List of ImageRecord, sorted by relative path for determinism.
    """
    if extensions is None:
        extensions = DEFAULT_EXTENSIONS

    # Normalize extensions to lowercase
    extensions = {ext.lower() for ext in extensions}

    root_path = root_path.resolve()
    images: list[ImageRecord] = []

    for file_path in root_path.rglob("*"):
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in extensions:
            continue

        relative = file_path.relative_to(root_path)
        image_id = compute_image_id(file_path)

        images.append(
            ImageRecord(
                image_id=image_id,
                file_path=file_path,
                relative_path=str(relative),
                filename=file_path.name,
            )
        )

    # Sort by relative path for deterministic ordering
    images.sort(key=lambda img: img.relative_path)

    return images
