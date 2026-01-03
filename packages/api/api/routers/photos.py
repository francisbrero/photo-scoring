"""Photos router for fetching and serving scored photos."""

import hashlib
import uuid
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from ..dependencies import CurrentUser, SupabaseClient
from ..services.credits import CreditService, InsufficientCreditsError
from ..services.openrouter import InferenceError, OpenRouterService

router = APIRouter()


class PhotoResponse(BaseModel):
    """Scored photo information."""

    id: str
    image_path: str  # Storage path relative to user folder
    original_filename: str | None  # Original filename when uploaded
    image_url: str | None  # Signed URL for displaying the image
    final_score: float | None
    aesthetic_score: float | None
    technical_score: float | None
    # Individual attribute scores (0-1 scale)
    composition: float | None
    subject_strength: float | None
    visual_appeal: float | None
    sharpness: float | None
    exposure_balance: float | None
    noise_level: float | None
    # Metadata
    description: str | None
    explanation: str | None
    improvements: str | None
    scene_type: str | None
    lighting: str | None
    subject_position: str | None
    location_name: str | None
    location_country: str | None
    features_json: str | None  # JSON string for frontend compatibility
    # Legacy model-specific scores (deprecated)
    qwen_aesthetic: float | None
    gpt4o_aesthetic: float | None
    gemini_aesthetic: float | None
    created_at: datetime


class PhotosListResponse(BaseModel):
    """Paginated list of photos."""

    photos: list[PhotoResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


@router.get("", response_model=PhotosListResponse)
async def list_photos(
    user: CurrentUser,
    supabase: SupabaseClient,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(
        default="created_at", pattern="^(created_at|final_score|aesthetic_score|technical_score)$"
    ),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
):
    """Get scored photos for the authenticated user.

    Returns paginated list sorted by the specified field.
    """
    # Build query
    query = supabase.table("scored_photos").select("*", count="exact").eq("user_id", user.id)

    # Apply sorting
    if sort_order == "desc":
        query = query.order(sort_by, desc=True)
    else:
        query = query.order(sort_by)

    # Apply pagination
    query = query.range(offset, offset + limit - 1)

    result = query.execute()

    # Get total count
    total = result.count if result.count is not None else len(result.data)

    # Transform to response format
    photos = []
    for row in result.data:
        # Extract model scores from JSONB if present
        model_scores = row.get("model_scores") or {}

        # Generate signed URL for the image (valid for 1 hour)
        image_url = None
        storage_path = row.get("storage_path")
        if storage_path:
            try:
                signed_url_response = supabase.storage.from_("photos").create_signed_url(
                    storage_path, expires_in=3600
                )
                if signed_url_response and "signedURL" in signed_url_response:
                    image_url = signed_url_response["signedURL"]
            except Exception:
                pass  # Skip if signed URL generation fails

        photos.append(
            PhotoResponse(
                id=row["id"],
                image_path=row["storage_path"],
                original_filename=row.get("original_filename"),
                image_url=image_url,
                final_score=row.get("final_score"),
                aesthetic_score=row.get("aesthetic_score"),
                technical_score=row.get("technical_score"),
                # Individual attribute scores from model_scores JSONB
                composition=model_scores.get("composition"),
                subject_strength=model_scores.get("subject_strength"),
                visual_appeal=model_scores.get("visual_appeal"),
                sharpness=model_scores.get("sharpness"),
                exposure_balance=model_scores.get("exposure_balance"),
                noise_level=model_scores.get("noise_level"),
                description=row.get("description"),
                explanation=row.get("explanation"),
                improvements=row.get("improvements"),
                scene_type=row.get("scene_type"),
                lighting=row.get("lighting"),
                subject_position=row.get("subject_position"),
                location_name=row.get("location_name"),
                location_country=row.get("location_country"),
                features_json=str(row.get("features_json")) if row.get("features_json") else None,
                qwen_aesthetic=model_scores.get("qwen_aesthetic"),
                gpt4o_aesthetic=model_scores.get("gpt4o_aesthetic"),
                gemini_aesthetic=model_scores.get("gemini_aesthetic"),
                created_at=row["created_at"],
            )
        )

    return PhotosListResponse(
        photos=photos,
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(photos) < total,
    )


@router.get("/{photo_id}", response_model=PhotoResponse)
async def get_photo(
    photo_id: str,
    user: CurrentUser,
    supabase: SupabaseClient,
):
    """Get a single photo by ID."""
    result = (
        supabase.table("scored_photos")
        .select("*")
        .eq("id", photo_id)
        .eq("user_id", user.id)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found",
        )

    row = result.data[0]
    model_scores = row.get("model_scores") or {}

    # Generate signed URL for the image (valid for 1 hour)
    image_url = None
    storage_path = row.get("storage_path")
    if storage_path:
        try:
            signed_url_response = supabase.storage.from_("photos").create_signed_url(
                storage_path, expires_in=3600
            )
            if signed_url_response and "signedURL" in signed_url_response:
                image_url = signed_url_response["signedURL"]
        except Exception:
            pass  # Skip if signed URL generation fails

    return PhotoResponse(
        id=row["id"],
        image_path=row["storage_path"],
        original_filename=row.get("original_filename"),
        image_url=image_url,
        final_score=row.get("final_score"),
        aesthetic_score=row.get("aesthetic_score"),
        technical_score=row.get("technical_score"),
        # Individual attribute scores from model_scores JSONB
        composition=model_scores.get("composition"),
        subject_strength=model_scores.get("subject_strength"),
        visual_appeal=model_scores.get("visual_appeal"),
        sharpness=model_scores.get("sharpness"),
        exposure_balance=model_scores.get("exposure_balance"),
        noise_level=model_scores.get("noise_level"),
        description=row.get("description"),
        explanation=row.get("explanation"),
        improvements=row.get("improvements"),
        scene_type=row.get("scene_type"),
        lighting=row.get("lighting"),
        subject_position=row.get("subject_position"),
        location_name=row.get("location_name"),
        location_country=row.get("location_country"),
        features_json=str(row.get("features_json")) if row.get("features_json") else None,
        qwen_aesthetic=model_scores.get("qwen_aesthetic"),
        gpt4o_aesthetic=model_scores.get("gpt4o_aesthetic"),
        gemini_aesthetic=model_scores.get("gemini_aesthetic"),
        created_at=row["created_at"],
    )


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    photo_id: str,
    user: CurrentUser,
    supabase: SupabaseClient,
):
    """Delete a scored photo.

    Also deletes the image from Supabase Storage.
    """
    # First get the photo to find storage path
    result = (
        supabase.table("scored_photos")
        .select("storage_path")
        .eq("id", photo_id)
        .eq("user_id", user.id)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found",
        )

    storage_path = result.data[0]["storage_path"]

    # Delete from storage
    try:
        supabase.storage.from_("photos").remove([storage_path])
    except Exception:
        # Log but don't fail if storage delete fails
        pass

    # Delete from database
    supabase.table("scored_photos").delete().eq("id", photo_id).eq("user_id", user.id).execute()

    return None


@router.get("/{photo_id}/image")
async def get_photo_image(
    photo_id: str,
    user: CurrentUser,
    supabase: SupabaseClient,
):
    """Get a signed URL for the photo image.

    Returns a redirect to a signed Supabase Storage URL.
    The signed URL is valid for 1 hour.
    """
    # First verify the photo belongs to the user
    result = (
        supabase.table("scored_photos")
        .select("storage_path")
        .eq("id", photo_id)
        .eq("user_id", user.id)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found",
        )

    storage_path = result.data[0]["storage_path"]

    # Generate signed URL (valid for 1 hour)
    try:
        signed_url_response = supabase.storage.from_("photos").create_signed_url(
            storage_path, expires_in=3600
        )

        if not signed_url_response or "signedURL" not in signed_url_response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate signed URL",
            )

        return RedirectResponse(
            url=signed_url_response["signedURL"],
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage error: {str(e)}",
        ) from e


class UploadResponse(BaseModel):
    """Response after uploading a photo."""

    id: str
    storage_path: str
    message: str


class ScoreResponse(BaseModel):
    """Response after scoring a photo."""

    id: str
    final_score: float | None
    aesthetic_score: float | None
    technical_score: float | None
    description: str | None
    credits_remaining: int


class ScoreDirectRequest(BaseModel):
    """Request to score an image without storing it."""

    image_data: str  # Base64-encoded image
    image_hash: str | None = None  # Optional, computed if not provided


class ScoreDirectResponse(BaseModel):
    """Full scoring response without storage."""

    image_hash: str
    final_score: float
    aesthetic_score: float
    technical_score: float
    # Individual attributes
    composition: float
    subject_strength: float
    visual_appeal: float
    sharpness: float
    exposure_balance: float
    noise_level: float
    # Critique and metadata
    explanation: str
    improvements: list[str]
    description: str
    # Credits
    credits_remaining: int
    cached: bool


class ScoringWeights(BaseModel):
    """Custom weights for rescoring photos."""

    # Aesthetic attribute weights (should sum to 1.0)
    composition: float = Field(default=0.4, ge=0.0, le=1.0)
    subject_strength: float = Field(default=0.35, ge=0.0, le=1.0)
    visual_appeal: float = Field(default=0.25, ge=0.0, le=1.0)
    # Technical attribute weights (should sum to 1.0)
    sharpness: float = Field(default=0.4, ge=0.0, le=1.0)
    exposure_balance: float = Field(default=0.35, ge=0.0, le=1.0)
    noise_level: float = Field(default=0.25, ge=0.0, le=1.0)
    # Category weights (should sum to 1.0)
    aesthetic_weight: float = Field(default=0.6, ge=0.0, le=1.0)
    technical_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    # Threshold penalties
    sharpness_threshold: float = Field(default=0.2, ge=0.0, le=1.0)
    exposure_threshold: float = Field(default=0.1, ge=0.0, le=1.0)


class RescoreRequest(BaseModel):
    """Request body for rescoring photos."""

    photo_ids: list[str] | None = Field(
        None, description="List of photo IDs to rescore. If None, rescore all photos."
    )
    weights: ScoringWeights = Field(
        default_factory=ScoringWeights,
        description="Custom scoring weights. Uses defaults if not provided.",
    )
    persist: bool = Field(
        default=False,
        description="If true, update stored scores in database.",
    )


class RescoredPhoto(BaseModel):
    """A photo with recomputed scores."""

    id: str
    final_score: float
    aesthetic_score: float
    technical_score: float
    # Raw attributes for reference
    composition: float | None
    subject_strength: float | None
    visual_appeal: float | None
    sharpness: float | None
    exposure_balance: float | None
    noise_level: float | None


class RescoreResponse(BaseModel):
    """Response from rescoring operation."""

    photos: list[RescoredPhoto]
    total_rescored: int
    skipped: int
    persisted: bool


@router.post("/upload", response_model=UploadResponse)
async def upload_photo(
    user: CurrentUser,
    supabase: SupabaseClient,
    file: UploadFile = File(...),
):
    """Upload a photo for scoring.

    The photo is stored in Supabase Storage and a record is created
    in the scored_photos table. Scoring is done separately via the
    /photos/{id}/score endpoint.

    HEIC/HEIF files are automatically converted to JPEG for browser compatibility.

    If the same image (by content hash) has already been uploaded by this user,
    returns the existing photo instead of creating a duplicate.
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/heic", "image/heif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported. Use: {', '.join(allowed_types)}",
        )

    # Read file content
    content = await file.read()

    # Check file size (50MB limit)
    max_size = 50 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 50MB limit",
        )

    # Convert HEIC/HEIF to JPEG for browser compatibility
    content_type = file.content_type
    file_ext = (
        file.filename.split(".")[-1].lower() if file.filename and "." in file.filename else "jpg"
    )

    if content_type in ["image/heic", "image/heif"] or file_ext in ["heic", "heif"]:
        from io import BytesIO

        from PIL import Image, ImageOps

        try:
            # pillow-heif is registered in openrouter service
            import pillow_heif

            pillow_heif.register_heif_opener()
        except ImportError:
            pass

        try:
            img = Image.open(BytesIO(content))
            img = ImageOps.exif_transpose(img)  # Fix orientation
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=90)
            content = buffer.getvalue()
            content_type = "image/jpeg"
            file_ext = "jpg"
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to process HEIC image: {str(e)}",
            ) from e

    # Compute image hash for deduplication
    image_hash = hashlib.sha256(content).hexdigest()

    # Check if this image already exists for this user
    existing = (
        supabase.table("scored_photos")
        .select("id, storage_path")
        .eq("user_id", user.id)
        .eq("image_hash", image_hash)
        .execute()
    )

    if existing.data:
        # Return existing photo instead of creating duplicate
        existing_photo = existing.data[0]
        return UploadResponse(
            id=existing_photo["id"],
            storage_path=existing_photo["storage_path"],
            message="Photo already exists. Returning existing photo.",
        )

    # Generate unique filename
    unique_id = str(uuid.uuid4())
    storage_path = f"{user.id}/{unique_id}.{file_ext}"

    # Upload to Supabase Storage
    try:
        supabase.storage.from_("photos").upload(
            storage_path,
            content,
            {"content-type": content_type},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}",
        ) from e

    # Create database record with image hash
    photo_id = unique_id
    try:
        supabase.table("scored_photos").insert(
            {
                "id": photo_id,
                "user_id": user.id,
                "storage_path": storage_path,
                "original_filename": file.filename,
                "image_hash": image_hash,
            }
        ).execute()
    except Exception as e:
        # Clean up storage on failure
        try:
            supabase.storage.from_("photos").remove([storage_path])
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create photo record: {str(e)}",
        ) from e

    return UploadResponse(
        id=photo_id,
        storage_path=storage_path,
        message="Photo uploaded successfully. Use /photos/{id}/score to score it.",
    )


@router.post("/score-direct", response_model=ScoreDirectResponse)
async def score_direct(
    request: ScoreDirectRequest,
    user: CurrentUser,
    supabase: SupabaseClient,
):
    """Score an image directly without storing it.

    This endpoint runs the full scoring pipeline (attributes, features,
    critique, metadata) on a base64-encoded image. The image is NOT stored
    in Supabase - only the inference results are cached.

    Perfect for desktop apps that keep photos local.

    Costs 1 credit per unique image. Cached results are free.
    """
    inference_service = OpenRouterService()

    # Decode image
    try:
        image_data = inference_service.decode_base64_image(request.image_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 image data: {str(e)}",
        ) from e

    # Compute hash
    image_hash = request.image_hash or inference_service.compute_image_hash(image_data)

    # Check inference cache
    cache_result = (
        supabase.table("inference_cache")
        .select("attributes, critique")
        .eq("user_id", user.id)
        .eq("image_hash", image_hash)
        .execute()
    )

    # Check features cache
    features_cache = (
        supabase.table("features_cache")
        .select("features")
        .eq("user_id", user.id)
        .eq("image_hash", image_hash)
        .execute()
    )

    # Check metadata cache
    metadata_cache = (
        supabase.table("metadata_cache")
        .select("metadata")
        .eq("user_id", user.id)
        .eq("image_hash", image_hash)
        .execute()
    )

    credit_service = CreditService(supabase)
    cached = bool(cache_result.data)

    if cached:
        # Use cached attributes (free)
        cached_data = cache_result.data[0]
        attributes = cached_data["attributes"]
        cached_critique = cached_data.get("critique")
        new_balance = await credit_service.get_balance(user.id)
    else:
        # Deduct credit for new inference
        try:
            new_balance = await credit_service.deduct_credit(user.id, 1)
        except InsufficientCreditsError as e:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=str(e),
            ) from e

        # Run AI inference for attributes
        try:
            attributes = await inference_service.analyze_image(image_data, image_hash)
        except InferenceError as e:
            await credit_service.refund_credit(user.id, 1)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
                if e.retryable
                else status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=e.message,
            ) from e

        cached_critique = None

    # Compute scores
    scores = inference_service.compute_scores(attributes)

    # Get or extract features
    if features_cache.data:
        features = features_cache.data[0]["features"]
    else:
        try:
            features = await inference_service.extract_features(image_data)
            # Cache features
            try:
                supabase.table("features_cache").insert(
                    {"user_id": user.id, "image_hash": image_hash, "features": features}
                ).execute()
            except Exception:
                pass
        except InferenceError:
            features = {
                "scene_type": "other",
                "main_subject": "unclear",
                "subject_position": "center",
                "background": "unknown",
                "lighting": "unknown",
                "color_palette": "neutral",
                "depth_of_field": "medium",
                "time_of_day": "unknown",
            }

    # Get or generate critique
    if cached_critique:
        explanation = cached_critique.get("explanation", "")
        improvements = cached_critique.get("improvements", [])
    else:
        try:
            critique = await inference_service.generate_critique(
                image_data, features, attributes, scores["final_score"]
            )
            explanation = inference_service.format_explanation(critique)
            improvements = critique.get("could_improve", [])
            if critique.get("key_recommendation"):
                improvements.append(critique["key_recommendation"])
        except InferenceError:
            explanation = "Unable to generate detailed critique."
            improvements = []

    # Get or extract metadata
    if metadata_cache.data:
        metadata = metadata_cache.data[0]["metadata"]
        description = metadata.get("description", "")
    else:
        try:
            metadata = await inference_service.analyze_image_metadata(image_data, image_hash)
            description = metadata.get("description", "")
            # Cache metadata
            try:
                supabase.table("metadata_cache").insert(
                    {"user_id": user.id, "image_hash": image_hash, "metadata": metadata}
                ).execute()
            except Exception:
                pass
        except InferenceError:
            description = ""

    # Cache inference results (if not already cached)
    if not cached:
        try:
            supabase.table("inference_cache").insert(
                {
                    "user_id": user.id,
                    "image_hash": image_hash,
                    "attributes": attributes,
                    "critique": {
                        "explanation": explanation,
                        "improvements": improvements,
                        "description": description,
                    },
                }
            ).execute()
        except Exception:
            pass

    return ScoreDirectResponse(
        image_hash=image_hash,
        final_score=scores["final_score"],
        aesthetic_score=scores["aesthetic_score"],
        technical_score=scores["technical_score"],
        composition=attributes.get("composition", 0.5),
        subject_strength=attributes.get("subject_strength", 0.5),
        visual_appeal=attributes.get("visual_appeal", 0.5),
        sharpness=attributes.get("sharpness", 0.5),
        exposure_balance=attributes.get("exposure_balance", 0.5),
        noise_level=attributes.get("noise_level", 0.5),
        explanation=explanation,
        improvements=improvements,
        description=description,
        credits_remaining=new_balance,
        cached=cached,
    )


@router.post("/{photo_id}/score", response_model=ScoreResponse)
async def score_photo(
    photo_id: str,
    user: CurrentUser,
    supabase: SupabaseClient,
):
    """Score a previously uploaded photo.

    This endpoint deducts 1 credit from the user's balance and
    triggers the scoring pipeline. For now, it generates placeholder
    scores until the inference proxy is implemented.
    """
    # Verify photo exists and belongs to user
    result = (
        supabase.table("scored_photos")
        .select("*")
        .eq("id", photo_id)
        .eq("user_id", user.id)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found",
        )

    photo = result.data[0]

    # Check if already scored
    if photo.get("final_score") is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Photo has already been scored",
        )

    storage_path = photo["storage_path"]

    # Download image from Supabase Storage
    try:
        download_result = supabase.storage.from_("photos").download(storage_path)
        # Supabase returns bytes directly, but ensure we have bytes
        if isinstance(download_result, bytes):
            image_data = download_result
        elif hasattr(download_result, "read"):
            image_data = download_result.read()
        else:
            image_data = bytes(download_result)

        # Debug: Log image data info
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"Downloaded image: {len(image_data)} bytes")
        logger.info(f"First 50 bytes: {image_data[:50]}")
        logger.info(f"Image data type: {type(image_data)}")

        # Check for common image signatures
        if image_data[:2] == b"\xff\xd8":
            logger.info("Detected JPEG signature")
        elif image_data[:8] == b"\x89PNG\r\n\x1a\n":
            logger.info("Detected PNG signature")
        elif image_data[:4] == b"RIFF" and image_data[8:12] == b"WEBP":
            logger.info("Detected WebP signature")
        else:
            logger.warning(f"Unknown image format, first bytes: {image_data[:20].hex()}")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download image: {str(e)}",
        ) from e

    # Compute image hash for caching
    image_hash = hashlib.sha256(image_data).hexdigest()

    # Check caches for inference results and features
    cache_result = (
        supabase.table("inference_cache")
        .select("attributes")
        .eq("user_id", user.id)
        .eq("image_hash", image_hash)
        .execute()
    )

    features_cache = (
        supabase.table("features_cache")
        .select("features")
        .eq("user_id", user.id)
        .eq("image_hash", image_hash)
        .execute()
    )

    credit_service = CreditService(supabase)
    inference_service = OpenRouterService()
    cached_attributes = bool(cache_result.data)
    cached_features = bool(features_cache.data)

    if cached_attributes:
        # Use cached attributes (free)
        attributes = cache_result.data[0]["attributes"]
        new_balance = await credit_service.get_balance(user.id)
    else:
        # Deduct credit for new inference
        try:
            new_balance = await credit_service.deduct_credit(user.id, 1)
        except InsufficientCreditsError as e:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=str(e),
            ) from e

        # Run AI inference
        try:
            attributes = await inference_service.analyze_image(image_data, image_hash)
        except InferenceError as e:
            # Refund on failure
            await credit_service.refund_credit(user.id, 1)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
                if e.retryable
                else status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=e.message,
            ) from e

        # Cache the inference result
        try:
            supabase.table("inference_cache").insert(
                {
                    "user_id": user.id,
                    "image_hash": image_hash,
                    "attributes": attributes,
                }
            ).execute()
        except Exception:
            pass  # Don't fail if caching fails

    # Extract features (for rich critique context)
    if cached_features:
        features = features_cache.data[0]["features"]
    else:
        try:
            features = await inference_service.extract_features(image_data)
            # Cache features
            try:
                supabase.table("features_cache").insert(
                    {
                        "user_id": user.id,
                        "image_hash": image_hash,
                        "features": features,
                    }
                ).execute()
            except Exception:
                pass
        except InferenceError:
            # Features extraction is optional, use defaults
            features = {
                "scene_type": "other",
                "main_subject": "unclear",
                "subject_position": "center",
                "background": "unknown",
                "lighting": "unknown",
                "color_palette": "neutral",
                "depth_of_field": "medium",
                "time_of_day": "unknown",
            }

    # Compute scores from attributes
    scores = inference_service.compute_scores(attributes)

    # Generate rich critique with full context (features + scores)
    try:
        critique = await inference_service.generate_critique(
            image_data, features, attributes, scores["final_score"]
        )
        explanation = inference_service.format_explanation(critique)
        improvements = inference_service.format_improvements(critique)
    except InferenceError:
        # Fall back to simple explanation if critique fails
        explanation = "Unable to generate detailed critique."
        improvements = "No specific improvements available."

    # Get metadata (description, location) - try cache first
    metadata_cache = (
        supabase.table("metadata_cache")
        .select("metadata")
        .eq("user_id", user.id)
        .eq("image_hash", image_hash)
        .execute()
    )

    description = None
    location_name = None
    location_country = None

    if metadata_cache.data:
        meta = metadata_cache.data[0]["metadata"]
        description = meta.get("description")
        location_name = meta.get("location_name")
        location_country = meta.get("location_country")
    else:
        # Run metadata inference (uses cheaper model, shares credit with main inference)
        try:
            metadata = await inference_service.analyze_image_metadata(image_data, image_hash)
            description = metadata.get("description")
            location_name = metadata.get("location_name")
            location_country = metadata.get("location_country")

            # Cache metadata
            try:
                supabase.table("metadata_cache").insert(
                    {
                        "user_id": user.id,
                        "image_hash": image_hash,
                        "metadata": metadata,
                    }
                ).execute()
            except Exception:
                pass
        except InferenceError:
            # Metadata extraction is optional, don't fail the whole request
            pass

    # Update photo with scores, metadata, explanation, improvements, and features
    supabase.table("scored_photos").update(
        {
            "final_score": scores["final_score"],
            "aesthetic_score": scores["aesthetic_score"],
            "technical_score": scores["technical_score"],
            "description": description,
            "explanation": explanation,
            "improvements": improvements,
            "location_name": location_name,
            "location_country": location_country,
            "model_scores": {
                "composition": attributes.get("composition"),
                "subject_strength": attributes.get("subject_strength"),
                "visual_appeal": attributes.get("visual_appeal"),
                "sharpness": attributes.get("sharpness"),
                "exposure_balance": attributes.get("exposure_balance"),
                "noise_level": attributes.get("noise_level"),
            },
            "features_json": features,
            "updated_at": "now()",
        }
    ).eq("id", photo_id).execute()

    return ScoreResponse(
        id=photo_id,
        final_score=scores["final_score"],
        aesthetic_score=scores["aesthetic_score"],
        technical_score=scores["technical_score"],
        description=description or "Photo analyzed successfully.",
        credits_remaining=new_balance,
    )


def compute_scores_with_weights(attributes: dict, weights: ScoringWeights) -> dict:
    """Compute scores from attributes using custom weights.

    Args:
        attributes: Dict with the 6 normalized attributes (0-1 scale)
        weights: Custom scoring weights

    Returns:
        Dictionary with aesthetic_score, technical_score, final_score
    """
    # Get attribute values with defaults
    composition = attributes.get("composition", 0.5)
    subject_strength = attributes.get("subject_strength", 0.5)
    visual_appeal = attributes.get("visual_appeal", 0.5)
    sharpness = attributes.get("sharpness", 0.5)
    exposure_balance = attributes.get("exposure_balance", 0.5)
    noise_level = attributes.get("noise_level", 0.5)

    # Aesthetic score (0-1)
    aesthetic_score = (
        composition * weights.composition
        + subject_strength * weights.subject_strength
        + visual_appeal * weights.visual_appeal
    )

    # Technical score (0-1)
    technical_score = (
        sharpness * weights.sharpness
        + exposure_balance * weights.exposure_balance
        + noise_level * weights.noise_level
    )

    # Final score (0-100)
    final_score = (
        aesthetic_score * weights.aesthetic_weight + technical_score * weights.technical_weight
    ) * 100

    # Apply threshold penalties
    if sharpness < weights.sharpness_threshold:
        penalty = (weights.sharpness_threshold - sharpness) / weights.sharpness_threshold * 0.5
        final_score *= 1 - penalty

    if exposure_balance < weights.exposure_threshold:
        penalty = (weights.exposure_threshold - exposure_balance) / weights.exposure_threshold * 0.3
        final_score *= 1 - penalty

    return {
        "aesthetic_score": round(aesthetic_score, 4),
        "technical_score": round(technical_score, 4),
        "final_score": round(final_score, 2),
    }


@router.post("/rescore", response_model=RescoreResponse)
async def rescore_photos(
    request: RescoreRequest,
    user: CurrentUser,
    supabase: SupabaseClient,
):
    """Rescore photos using cached attributes with custom weights.

    This endpoint does NOT run any AI inference. It recomputes scores
    from previously cached attribute values using new weights.

    Use cases:
    - Experiment with different scoring weights without re-running inference
    - Adjust emphasis on composition vs technical quality
    - Apply stricter or looser threshold penalties

    The operation is free (no credits deducted) since no inference is performed.
    """
    # Build query for photos with cached attributes
    query = (
        supabase.table("scored_photos")
        .select("id, model_scores")
        .eq("user_id", user.id)
        .not_.is_("model_scores", "null")
    )

    # Filter by specific photo IDs if provided
    if request.photo_ids:
        query = query.in_("id", request.photo_ids)

    result = query.execute()

    if not result.data:
        return RescoreResponse(
            photos=[],
            total_rescored=0,
            skipped=0,
            persisted=False,
        )

    rescored_photos: list[RescoredPhoto] = []
    skipped = 0

    for photo in result.data:
        model_scores = photo.get("model_scores") or {}

        # Skip photos without attributes
        if not model_scores:
            skipped += 1
            continue

        # Compute new scores with custom weights
        new_scores = compute_scores_with_weights(model_scores, request.weights)

        rescored_photos.append(
            RescoredPhoto(
                id=photo["id"],
                final_score=new_scores["final_score"],
                aesthetic_score=new_scores["aesthetic_score"],
                technical_score=new_scores["technical_score"],
                composition=model_scores.get("composition"),
                subject_strength=model_scores.get("subject_strength"),
                visual_appeal=model_scores.get("visual_appeal"),
                sharpness=model_scores.get("sharpness"),
                exposure_balance=model_scores.get("exposure_balance"),
                noise_level=model_scores.get("noise_level"),
            )
        )

        # Persist updated scores if requested
        if request.persist:
            supabase.table("scored_photos").update(
                {
                    "final_score": new_scores["final_score"],
                    "aesthetic_score": new_scores["aesthetic_score"],
                    "technical_score": new_scores["technical_score"],
                    "updated_at": "now()",
                }
            ).eq("id", photo["id"]).execute()

    return RescoreResponse(
        photos=rescored_photos,
        total_rescored=len(rescored_photos),
        skipped=skipped,
        persisted=request.persist,
    )


@router.post("/{photo_id}/regenerate")
async def regenerate_explanation(
    photo_id: str,
    user: CurrentUser,
    supabase: SupabaseClient,
):
    """Regenerate explanation and improvements for a scored photo.

    This operation downloads the image and generates a new rich critique
    using the existing scores and features. This is a free operation
    (no credit deduction) but requires an API call for the critique.
    """
    # Get photo with existing scores
    result = (
        supabase.table("scored_photos")
        .select("*")
        .eq("id", photo_id)
        .eq("user_id", user.id)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found",
        )

    photo = result.data[0]
    model_scores = photo.get("model_scores") or {}
    features = photo.get("features_json") or {}
    storage_path = photo.get("storage_path")
    final_score = photo.get("final_score") or 0

    if not model_scores:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Photo has no scores to regenerate from",
        )

    inference_service = OpenRouterService()

    # Download image for rich critique generation
    try:
        download_result = supabase.storage.from_("photos").download(storage_path)
        if isinstance(download_result, bytes):
            image_data = download_result
        elif hasattr(download_result, "read"):
            image_data = download_result.read()
        else:
            image_data = bytes(download_result)

        # If no features cached, extract them now
        if not features:
            try:
                features = await inference_service.extract_features(image_data)
            except InferenceError:
                features = {
                    "scene_type": "other",
                    "main_subject": "unclear",
                    "subject_position": "center",
                    "background": "unknown",
                    "lighting": "unknown",
                    "color_palette": "neutral",
                    "depth_of_field": "medium",
                    "time_of_day": "unknown",
                }

        # Generate rich critique
        critique = await inference_service.generate_critique(
            image_data, features, model_scores, final_score
        )
        explanation = inference_service.format_explanation(critique)
        improvements = inference_service.format_improvements(critique)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate critique: {str(e)}",
        ) from e

    # Update the photo
    supabase.table("scored_photos").update(
        {
            "explanation": explanation,
            "improvements": improvements,
            "features_json": features,
            "updated_at": "now()",
        }
    ).eq("id", photo_id).execute()

    return {"message": "Explanation and improvements regenerated", "id": photo_id}


@router.post("/regenerate-all")
async def regenerate_all_explanations(
    user: CurrentUser,
    supabase: SupabaseClient,
):
    """Regenerate explanation and improvements for all scored photos.

    This operation downloads each image and generates new rich critiques
    using the existing scores and features. This is a free operation
    (no credit deduction) but requires API calls for each critique.

    Note: This can be slow for many photos due to API rate limits.
    """
    # Get all scored photos for user
    result = (
        supabase.table("scored_photos")
        .select("id, final_score, model_scores, features_json, storage_path")
        .eq("user_id", user.id)
        .not_.is_("final_score", "null")
        .execute()
    )

    if not result.data:
        return {"message": "No scored photos found", "updated": 0}

    inference_service = OpenRouterService()
    updated = 0
    failed = 0

    for photo in result.data:
        model_scores = photo.get("model_scores") or {}
        if not model_scores:
            continue

        features = photo.get("features_json") or {}
        storage_path = photo.get("storage_path")
        final_score = photo.get("final_score") or 0

        try:
            # Download image for rich critique generation
            download_result = supabase.storage.from_("photos").download(storage_path)
            if isinstance(download_result, bytes):
                image_data = download_result
            elif hasattr(download_result, "read"):
                image_data = download_result.read()
            else:
                image_data = bytes(download_result)

            # If no features cached, extract them now
            if not features:
                try:
                    features = await inference_service.extract_features(image_data)
                except InferenceError:
                    features = {
                        "scene_type": "other",
                        "main_subject": "unclear",
                        "subject_position": "center",
                        "background": "unknown",
                        "lighting": "unknown",
                        "color_palette": "neutral",
                        "depth_of_field": "medium",
                        "time_of_day": "unknown",
                    }

            # Generate rich critique
            critique = await inference_service.generate_critique(
                image_data, features, model_scores, final_score
            )
            explanation = inference_service.format_explanation(critique)
            improvements = inference_service.format_improvements(critique)

            supabase.table("scored_photos").update(
                {
                    "explanation": explanation,
                    "improvements": improvements,
                    "features_json": features,
                    "updated_at": "now()",
                }
            ).eq("id", photo["id"]).execute()
            updated += 1

        except Exception:
            failed += 1
            continue

    message = f"Regenerated {updated} photos"
    if failed > 0:
        message += f" ({failed} failed)"

    return {"message": message, "updated": updated, "failed": failed}


@router.get("/serve/{path:path}")
async def serve_photo_by_path(
    path: str,
    user: CurrentUser,
    supabase: SupabaseClient,
):
    """Serve a photo by its storage path.

    This endpoint is used by the frontend to serve images directly.
    The path should be the storage_path from the photo record.

    Returns a redirect to a signed Supabase Storage URL.
    """
    # Verify the photo belongs to the user by checking the database
    result = (
        supabase.table("scored_photos")
        .select("id")
        .eq("storage_path", path)
        .eq("user_id", user.id)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found or access denied",
        )

    # Generate signed URL (valid for 1 hour)
    try:
        signed_url_response = supabase.storage.from_("photos").create_signed_url(
            path, expires_in=3600
        )

        if not signed_url_response or "signedURL" not in signed_url_response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate signed URL",
            )

        return RedirectResponse(
            url=signed_url_response["signedURL"],
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage error: {str(e)}",
        ) from e
