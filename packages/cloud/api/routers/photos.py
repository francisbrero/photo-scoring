"""Photos router for fetching and serving scored photos."""

import hashlib
import uuid
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ..dependencies import CurrentUser, SupabaseClient
from ..services.credits import CreditService, InsufficientCreditsError
from ..services.openrouter import InferenceError, OpenRouterService

router = APIRouter()


class PhotoResponse(BaseModel):
    """Scored photo information."""

    id: str
    image_path: str  # Storage path relative to user folder
    final_score: float | None
    aesthetic_score: float | None
    technical_score: float | None
    description: str | None
    explanation: str | None
    improvements: str | None
    scene_type: str | None
    lighting: str | None
    subject_position: str | None
    location_name: str | None
    location_country: str | None
    features_json: str | None  # JSON string for frontend compatibility
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

        photos.append(
            PhotoResponse(
                id=row["id"],
                image_path=row["storage_path"],
                final_score=row.get("final_score"),
                aesthetic_score=row.get("aesthetic_score"),
                technical_score=row.get("technical_score"),
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

    return PhotoResponse(
        id=row["id"],
        image_path=row["storage_path"],
        final_score=row.get("final_score"),
        aesthetic_score=row.get("aesthetic_score"),
        technical_score=row.get("technical_score"),
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
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/heic", "image/heif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported. Use: {', '.join(allowed_types)}",
        )

    # Generate unique filename
    file_ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    unique_id = str(uuid.uuid4())
    storage_path = f"{user.id}/{unique_id}.{file_ext}"

    # Read file content
    content = await file.read()

    # Check file size (50MB limit)
    max_size = 50 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 50MB limit",
        )

    # Upload to Supabase Storage
    try:
        supabase.storage.from_("photos").upload(
            storage_path,
            content,
            {"content-type": file.content_type},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}",
        ) from e

    # Create database record
    photo_id = unique_id
    try:
        supabase.table("scored_photos").insert(
            {
                "id": photo_id,
                "user_id": user.id,
                "storage_path": storage_path,
                "original_filename": file.filename,
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download image: {str(e)}",
        ) from e

    # Compute image hash for caching
    image_hash = hashlib.sha256(image_data).hexdigest()

    # Check if we have cached inference results
    cache_result = (
        supabase.table("inference_cache")
        .select("attributes")
        .eq("user_id", user.id)
        .eq("image_hash", image_hash)
        .execute()
    )

    credit_service = CreditService(supabase)
    inference_service = OpenRouterService()
    cached = bool(cache_result.data)

    if cached:
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

    # Compute scores from attributes
    scores = inference_service.compute_scores(attributes)

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

    # Update photo with scores and metadata
    supabase.table("scored_photos").update(
        {
            "final_score": scores["final_score"],
            "aesthetic_score": scores["aesthetic_score"],
            "technical_score": scores["technical_score"],
            "description": description,
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
            "scored_at": "now()",
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
