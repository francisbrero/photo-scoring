"""Inference router for AI-powered photo analysis."""

import time
from collections import defaultdict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..dependencies import CurrentUser, SupabaseClient
from ..services.credits import CreditService, InsufficientCreditsError
from ..services.openrouter import InferenceError, OpenRouterService

router = APIRouter()

# Simple in-memory rate limiter (per user)
# In production, use Redis or similar
_rate_limits: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_REQUESTS = 10  # requests per window
RATE_LIMIT_WINDOW = 60  # seconds


def check_rate_limit(user_id: str) -> bool:
    """Check if user is within rate limits. Returns True if allowed."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    # Clean old entries
    _rate_limits[user_id] = [t for t in _rate_limits[user_id] if t > window_start]

    if len(_rate_limits[user_id]) >= RATE_LIMIT_REQUESTS:
        return False

    _rate_limits[user_id].append(now)
    return True


class AnalyzeRequest(BaseModel):
    """Request body for image analysis."""

    image_data: str = Field(..., description="Base64-encoded image data")
    image_hash: str | None = Field(
        None, description="SHA256 hash of image (computed if not provided)"
    )


class AttributesResponse(BaseModel):
    """Normalized image attributes from AI analysis."""

    image_id: str
    composition: float = Field(..., ge=0, le=1)
    subject_strength: float = Field(..., ge=0, le=1)
    visual_appeal: float = Field(..., ge=0, le=1)
    sharpness: float = Field(..., ge=0, le=1)
    exposure_balance: float = Field(..., ge=0, le=1)
    noise_level: float = Field(..., ge=0, le=1)
    model_name: str
    model_version: str


class ScoresResponse(BaseModel):
    """Computed scores from attributes."""

    aesthetic_score: float
    technical_score: float
    final_score: float


class CritiqueResponse(BaseModel):
    """Critique and recommendations from AI analysis."""

    explanation: str = ""
    improvements: list[str] = []
    description: str = ""


class AnalyzeResponse(BaseModel):
    """Response from image analysis."""

    attributes: AttributesResponse
    scores: ScoresResponse
    critique: CritiqueResponse | None = None
    credits_remaining: int
    cached: bool = Field(
        False, description="Whether result was retrieved from cache (no credit charged)"
    )


class MetadataRequest(BaseModel):
    """Request body for metadata extraction."""

    image_data: str = Field(..., description="Base64-encoded image data")
    image_hash: str | None = Field(None, description="SHA256 hash of image")


class MetadataResponse(BaseModel):
    """Image metadata from AI analysis."""

    description: str
    location_name: str | None
    location_country: str | None
    credits_remaining: int
    cached: bool = False


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_image(
    request: AnalyzeRequest,
    user: CurrentUser,
    supabase: SupabaseClient,
):
    """Analyze an image and return AI-generated attributes and scores.

    Costs 1 credit per unique image. Cached results are free.

    The image is analyzed for:
    - Aesthetic qualities: composition, subject strength, visual appeal
    - Technical qualities: sharpness, exposure balance, noise level

    Returns computed scores (aesthetic, technical, final) based on
    weighted averages of the attributes.
    """
    # Check rate limit
    if not check_rate_limit(user.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_REQUESTS} requests per minute.",
        )

    # Decode image and compute hash
    service = OpenRouterService()
    try:
        image_data = service.decode_base64_image(request.image_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 image data: {str(e)}",
        ) from e

    image_hash = request.image_hash or service.compute_image_hash(image_data)

    # Check cache first
    cache_result = (
        supabase.table("inference_cache")
        .select("attributes, critique")
        .eq("user_id", user.id)
        .eq("image_hash", image_hash)
        .execute()
    )

    credit_service = CreditService(supabase)

    if cache_result.data:
        # Return cached result (free)
        cached_data = cache_result.data[0]
        cached_attrs = cached_data["attributes"]
        scores = service.compute_scores(cached_attrs)
        balance = await credit_service.get_balance(user.id)

        # Get cached critique if available
        cached_critique = None
        if cached_data.get("critique"):
            cached_critique = CritiqueResponse(**cached_data["critique"])

        return AnalyzeResponse(
            attributes=AttributesResponse(**cached_attrs),
            scores=ScoresResponse(**scores),
            critique=cached_critique,
            credits_remaining=balance,
            cached=True,
        )

    # Check balance before inference
    balance = await credit_service.get_balance(user.id)
    if balance < 1:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits. Please purchase more credits to continue.",
        )

    # Deduct credit optimistically
    try:
        new_balance = await credit_service.deduct_credit(user.id, 1)
    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e),
        ) from e

    # Run inference
    try:
        attributes = await service.analyze_image(image_data, image_hash)
    except InferenceError as e:
        # Refund on failure
        await credit_service.refund_credit(user.id, 1)
        status_code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if e.retryable
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(status_code=status_code, detail=e.message) from e

    # Compute scores
    scores = service.compute_scores(attributes)

    # Generate critique (best effort - don't fail if it fails)
    critique_data = None
    try:
        # Extract features for context
        features = await service.extract_features(image_data)

        # Generate critique
        critique = await service.generate_critique(
            image_data, features, attributes, scores["final_score"]
        )

        # Format the critique
        explanation = service.format_explanation(critique)
        improvements = critique.get("could_improve", [])
        if critique.get("key_recommendation"):
            improvements.append(critique["key_recommendation"])

        # Get description from metadata (cheaper call)
        try:
            metadata = await service.analyze_image_metadata(image_data, image_hash)
            description = metadata.get("description", "")
        except Exception:
            description = ""

        critique_data = CritiqueResponse(
            explanation=explanation,
            improvements=improvements,
            description=description,
        )
    except Exception as e:
        # Log but don't fail - critique is optional enhancement
        import logging

        logging.warning(f"Critique generation failed: {e}")

    # Cache the result (including critique if available)
    cache_data = {
        "user_id": user.id,
        "image_hash": image_hash,
        "attributes": attributes,
    }
    if critique_data:
        cache_data["critique"] = {
            "explanation": critique_data.explanation,
            "improvements": critique_data.improvements,
            "description": critique_data.description,
        }

    try:
        supabase.table("inference_cache").insert(cache_data).execute()
    except Exception:
        # Don't fail if caching fails, just log
        pass

    return AnalyzeResponse(
        attributes=AttributesResponse(**attributes),
        scores=ScoresResponse(**scores),
        critique=critique_data,
        credits_remaining=new_balance,
        cached=False,
    )


@router.post("/metadata", response_model=MetadataResponse)
async def extract_metadata(
    request: MetadataRequest,
    user: CurrentUser,
    supabase: SupabaseClient,
):
    """Extract metadata (description, location) from an image.

    Costs 1 credit per unique image. Cached results are free.

    Uses a smaller/cheaper model to generate:
    - A 1-3 sentence description of the image
    - Location name and country if identifiable
    """
    # Check rate limit
    if not check_rate_limit(user.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_REQUESTS} requests per minute.",
        )

    # Decode image and compute hash
    service = OpenRouterService()
    try:
        image_data = service.decode_base64_image(request.image_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 image data: {str(e)}",
        ) from e

    image_hash = request.image_hash or service.compute_image_hash(image_data)

    # Check cache first
    cache_result = (
        supabase.table("metadata_cache")
        .select("metadata")
        .eq("user_id", user.id)
        .eq("image_hash", image_hash)
        .execute()
    )

    credit_service = CreditService(supabase)

    if cache_result.data:
        # Return cached result (free)
        cached_meta = cache_result.data[0]["metadata"]
        balance = await credit_service.get_balance(user.id)

        return MetadataResponse(
            **cached_meta,
            credits_remaining=balance,
            cached=True,
        )

    # Check balance before inference
    balance = await credit_service.get_balance(user.id)
    if balance < 1:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits. Please purchase more credits to continue.",
        )

    # Deduct credit optimistically
    try:
        new_balance = await credit_service.deduct_credit(user.id, 1)
    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e),
        ) from e

    # Run inference
    try:
        metadata = await service.analyze_image_metadata(image_data, image_hash)
    except InferenceError as e:
        # Refund on failure
        await credit_service.refund_credit(user.id, 1)
        status_code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if e.retryable
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(status_code=status_code, detail=e.message) from e

    # Cache the result
    try:
        supabase.table("metadata_cache").insert(
            {
                "user_id": user.id,
                "image_hash": image_hash,
                "metadata": metadata,
            }
        ).execute()
    except Exception:
        # Don't fail if caching fails
        pass

    return MetadataResponse(
        **metadata,
        credits_remaining=new_balance,
        cached=False,
    )
