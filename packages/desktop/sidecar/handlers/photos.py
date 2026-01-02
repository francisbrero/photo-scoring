"""Photo discovery and thumbnail handlers."""

import base64
import io
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from PIL import Image, ExifTags
from PIL.ImageOps import exif_transpose

from photo_score.ingestion.discover import discover_images, compute_image_id
from photo_score.ingestion.metadata import extract_exif

router = APIRouter()


class ImageRecord(BaseModel):
    """Image record with metadata."""

    image_id: str
    file_path: str
    filename: str
    relative_path: str


class DiscoverResponse(BaseModel):
    """Response for image discovery."""

    images: list[ImageRecord]
    total: int


class ThumbnailResponse(BaseModel):
    """Response for thumbnail generation."""

    image_id: str
    data: str  # base64 encoded
    width: int
    height: int
    format: str


class MetadataResponse(BaseModel):
    """Response for image metadata."""

    image_id: str
    exif: Optional[dict]
    file_size: int
    dimensions: Optional[tuple[int, int]]


@router.get("/discover", response_model=DiscoverResponse)
async def discover(
    directory: str = Query(..., description="Directory path to scan for images"),
):
    """Discover images in a directory."""
    dir_path = Path(directory)

    if not dir_path.exists():
        raise HTTPException(status_code=404, detail=f"Directory not found: {directory}")

    if not dir_path.is_dir():
        raise HTTPException(
            status_code=400, detail=f"Path is not a directory: {directory}"
        )

    try:
        records = discover_images(dir_path)
        images = [
            ImageRecord(
                image_id=r.image_id,
                file_path=str(r.file_path),
                filename=r.filename,
                relative_path=r.relative_path,
            )
            for r in records
        ]
        return DiscoverResponse(images=images, total=len(images))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/thumbnail", response_model=ThumbnailResponse)
async def get_thumbnail(
    path: str = Query(..., description="Path to the image file"),
    size: int = Query(300, description="Maximum dimension for thumbnail"),
):
    """Generate a thumbnail for an image."""
    file_path = Path(path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Image not found: {path}")

    try:
        # Handle HEIC files
        if file_path.suffix.lower() in (".heic", ".heif"):
            import pillow_heif

            pillow_heif.register_heif_opener()

        with Image.open(file_path) as img:
            # Apply EXIF orientation to fix rotation
            img = exif_transpose(img)

            # Convert to RGB if necessary
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Create thumbnail
            img.thumbnail((size, size), Image.Resampling.LANCZOS)

            # Save to bytes
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            buffer.seek(0)

            image_id = compute_image_id(file_path)

            return ThumbnailResponse(
                image_id=image_id,
                data=base64.b64encode(buffer.getvalue()).decode("utf-8"),
                width=img.width,
                height=img.height,
                format="jpeg",
            )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate thumbnail: {e}"
        )


class FullImageResponse(BaseModel):
    """Response for full resolution image."""

    image_id: str
    data: str  # base64 encoded
    width: int
    height: int
    format: str


@router.get("/full", response_model=FullImageResponse)
async def get_full_image(
    path: str = Query(..., description="Path to the image file"),
    max_size: int = Query(2000, description="Maximum dimension (width or height)"),
):
    """Get a full resolution image (scaled to max_size)."""
    file_path = Path(path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Image not found: {path}")

    try:
        # Handle HEIC files
        if file_path.suffix.lower() in (".heic", ".heif"):
            import pillow_heif

            pillow_heif.register_heif_opener()

        with Image.open(file_path) as img:
            # Apply EXIF orientation to fix rotation
            img = exif_transpose(img)

            # Convert to RGB if necessary
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Scale down if larger than max_size
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            # Save to bytes
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=92)
            buffer.seek(0)

            image_id = compute_image_id(file_path)

            return FullImageResponse(
                image_id=image_id,
                data=base64.b64encode(buffer.getvalue()).decode("utf-8"),
                width=img.width,
                height=img.height,
                format="jpeg",
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load full image: {e}")


@router.get("/metadata", response_model=MetadataResponse)
async def get_metadata(
    path: str = Query(..., description="Path to the image file"),
):
    """Get metadata for an image."""
    file_path = Path(path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Image not found: {path}")

    try:
        image_id = compute_image_id(file_path)
        exif = extract_exif(file_path)
        file_size = file_path.stat().st_size

        # Get dimensions
        dimensions = None
        try:
            if file_path.suffix.lower() in (".heic", ".heif"):
                import pillow_heif

                pillow_heif.register_heif_opener()

            with Image.open(file_path) as img:
                dimensions = (img.width, img.height)
        except Exception:
            pass

        return MetadataResponse(
            image_id=image_id,
            exif=exif,
            file_size=file_size,
            dimensions=dimensions,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metadata: {e}")
