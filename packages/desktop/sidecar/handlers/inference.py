"""Inference and scoring handlers using cloud API."""

import sys
from pathlib import Path
from typing import Optional

# Get root path for config files - handle PyInstaller bundle
if getattr(sys, "frozen", False):
    # Running as compiled executable
    ROOT_PATH = Path(sys._MEIPASS)
else:
    # Running in development
    ROOT_PATH = Path(__file__).parent.parent.parent.parent.parent
DEFAULT_CONFIG = ROOT_PATH / "configs" / "default.yaml"

from fastapi import APIRouter, HTTPException, Query  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from photo_score.ingestion.discover import compute_image_id  # noqa: E402
from photo_score.storage.cache import Cache  # noqa: E402
from photo_score.storage.models import NormalizedAttributes  # noqa: E402
from photo_score.config.loader import load_config  # noqa: E402
from photo_score.scoring.reducer import ScoringReducer  # noqa: E402
from photo_score.scoring.explanations import ExplanationGenerator  # noqa: E402

from .cloud_client import (  # noqa: E402
    score_image as cloud_score_image,
    CloudInferenceError,
    InsufficientCreditsError,
    AuthenticationError,
)
from .auth import get_auth_token  # noqa: E402

router = APIRouter()


class ScoreRequest(BaseModel):
    """Request to score an image."""

    image_path: str
    config_path: Optional[str] = None


class AttributesResponse(BaseModel):
    """Normalized attributes for an image."""

    image_id: str
    composition: float
    subject_strength: float
    visual_appeal: float
    sharpness: float
    exposure_balance: float
    noise_level: float
    model_name: Optional[str] = None
    model_version: Optional[str] = None


class ScoreResponse(BaseModel):
    """Scoring result for an image."""

    image_id: str
    image_path: str
    final_score: float
    aesthetic_score: float
    technical_score: float
    attributes: AttributesResponse
    explanation: str
    improvements: list[str] = []
    description: str = ""
    cached: bool
    credits_remaining: Optional[int] = None


class BatchScoreRequest(BaseModel):
    """Request to score multiple images."""

    image_paths: list[str]
    config_path: Optional[str] = None


class BatchScoreResponse(BaseModel):
    """Response for batch scoring."""

    results: list[ScoreResponse]
    total: int
    cached: int
    scored: int


@router.get("/attributes", response_model=Optional[AttributesResponse])
async def get_attributes(
    path: str = Query(..., description="Path to the image file"),
):
    """Get cached attributes for an image."""
    file_path = Path(path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Image not found: {path}")

    try:
        image_id = compute_image_id(file_path)
        cache = Cache()
        attrs = cache.get_attributes(image_id)

        if attrs is None:
            return None

        return AttributesResponse(
            image_id=attrs.image_id,
            composition=attrs.composition,
            subject_strength=attrs.subject_strength,
            visual_appeal=attrs.visual_appeal,
            sharpness=attrs.sharpness,
            exposure_balance=attrs.exposure_balance,
            noise_level=attrs.noise_level,
            model_name=attrs.model_name,
            model_version=attrs.model_version,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/score", response_model=ScoreResponse)
async def score_image(request: ScoreRequest):
    """Score a single image using cloud API."""
    file_path = Path(request.image_path)

    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Image not found: {request.image_path}"
        )

    # Check for authentication
    if not get_auth_token():
        raise HTTPException(
            status_code=401,
            detail="Not logged in. Please log in to score photos.",
        )

    try:
        image_id = compute_image_id(file_path)
        cache = Cache()
        cached = False
        credits_remaining = None

        # Check cache first
        attrs = cache.get_attributes(image_id)

        # Variables for critique data
        critique_explanation = ""
        improvements: list[str] = []
        description = ""

        if attrs is None:
            # Need to run scoring via cloud API
            try:
                result = await cloud_score_image(str(file_path), image_id)

                # Extract attributes from cloud response
                attrs = NormalizedAttributes(
                    image_id=image_id,
                    composition=result["composition"],
                    subject_strength=result["subject_strength"],
                    visual_appeal=result["visual_appeal"],
                    sharpness=result["sharpness"],
                    exposure_balance=result["exposure_balance"],
                    noise_level=result["noise_level"],
                    model_name="cloud",
                    model_version="v1",
                )
                cache.store_attributes(attrs)

                # Get credits remaining from response
                credits_remaining = result.get("credits_remaining")

                # Extract critique from cloud response
                critique_explanation = result.get("explanation", "")
                improvements = result.get("improvements", [])
                description = result.get("description", "")

                # Cache the critique
                if critique_explanation or improvements or description:
                    cache.store_critique(
                        image_id,
                        {
                            "explanation": critique_explanation,
                            "improvements": improvements,
                            "description": description,
                        },
                    )

            except AuthenticationError as e:
                raise HTTPException(status_code=401, detail=e.message)
            except InsufficientCreditsError as e:
                raise HTTPException(status_code=402, detail=e.message)
            except CloudInferenceError as e:
                raise HTTPException(status_code=e.status_code, detail=e.message)
        else:
            cached = True
            # Try to load cached critique
            cached_critique = cache.get_critique(image_id)
            if cached_critique:
                critique_explanation = cached_critique["explanation"]
                improvements = cached_critique["improvements"]
                description = cached_critique["description"]

        # Load config and compute score
        config_path = (
            Path(request.config_path) if request.config_path else DEFAULT_CONFIG
        )
        config = load_config(config_path)
        reducer = ScoringReducer(config)
        score_result = reducer.compute_scores(image_id, str(file_path), attrs)

        # Use critique explanation if available, otherwise generate basic one
        if critique_explanation:
            explanation = critique_explanation
        else:
            explainer = ExplanationGenerator(config)
            explanation = explainer.generate(
                attrs, score_result.contributions, score_result.final_score
            )

        return ScoreResponse(
            image_id=image_id,
            image_path=str(file_path),
            final_score=score_result.final_score,
            aesthetic_score=score_result.aesthetic_score,
            technical_score=score_result.technical_score,
            attributes=AttributesResponse(
                image_id=attrs.image_id,
                composition=attrs.composition,
                subject_strength=attrs.subject_strength,
                visual_appeal=attrs.visual_appeal,
                sharpness=attrs.sharpness,
                exposure_balance=attrs.exposure_balance,
                noise_level=attrs.noise_level,
                model_name=attrs.model_name,
                model_version=attrs.model_version,
            ),
            explanation=explanation,
            improvements=improvements,
            description=description,
            cached=cached,
            credits_remaining=credits_remaining,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rescore", response_model=ScoreResponse)
async def rescore_image(request: ScoreRequest):
    """Rescore an image using cached attributes (no API call)."""
    file_path = Path(request.image_path)

    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Image not found: {request.image_path}"
        )

    try:
        image_id = compute_image_id(file_path)
        cache = Cache()

        attrs = cache.get_attributes(image_id)
        if attrs is None:
            raise HTTPException(
                status_code=404,
                detail="No cached attributes found. Run score first.",
            )

        # Load config and compute score
        config_path = (
            Path(request.config_path) if request.config_path else DEFAULT_CONFIG
        )
        config = load_config(config_path)
        reducer = ScoringReducer(config)
        score_result = reducer.compute_scores(image_id, str(file_path), attrs)

        # Generate explanation
        explainer = ExplanationGenerator(config)
        explanation = explainer.generate(
            attrs, score_result.contributions, score_result.final_score
        )

        return ScoreResponse(
            image_id=image_id,
            image_path=str(file_path),
            final_score=score_result.final_score,
            aesthetic_score=score_result.aesthetic_score,
            technical_score=score_result.technical_score,
            attributes=AttributesResponse(
                image_id=attrs.image_id,
                composition=attrs.composition,
                subject_strength=attrs.subject_strength,
                visual_appeal=attrs.visual_appeal,
                sharpness=attrs.sharpness,
                exposure_balance=attrs.exposure_balance,
                noise_level=attrs.noise_level,
                model_name=attrs.model_name,
                model_version=attrs.model_version,
            ),
            explanation=explanation,
            cached=True,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CachedScoreRequest(BaseModel):
    """Request to get cached scores for multiple images."""

    image_paths: list[str]


class CachedScoreResponse(BaseModel):
    """Response with cached scores (null if not cached)."""

    scores: dict[str, Optional[ScoreResponse]]


@router.post("/cached-scores", response_model=CachedScoreResponse)
async def get_cached_scores(request: CachedScoreRequest):
    """Get cached scores for multiple images without running inference."""
    scores: dict[str, Optional[ScoreResponse]] = {}

    for image_path in request.image_paths:
        file_path = Path(image_path)
        if not file_path.exists():
            scores[image_path] = None
            continue

        try:
            image_id = compute_image_id(file_path)
            cache = Cache()
            attrs = cache.get_attributes(image_id)

            if attrs is None:
                scores[image_path] = None
                continue

            # Load config and compute score from cached attributes
            config = load_config(DEFAULT_CONFIG)
            reducer = ScoringReducer(config)
            score_result = reducer.compute_scores(image_id, str(file_path), attrs)

            # Try to get cached critique
            cached_critique = cache.get_critique(image_id)
            if cached_critique:
                explanation = cached_critique["explanation"]
                improvements = cached_critique["improvements"]
                description = cached_critique["description"]
            else:
                # Fall back to basic explanation
                explainer = ExplanationGenerator(config)
                explanation = explainer.generate(
                    attrs, score_result.contributions, score_result.final_score
                )
                improvements = []
                description = ""

            scores[image_path] = ScoreResponse(
                image_id=image_id,
                image_path=str(file_path),
                final_score=score_result.final_score,
                aesthetic_score=score_result.aesthetic_score,
                technical_score=score_result.technical_score,
                attributes=AttributesResponse(
                    image_id=attrs.image_id,
                    composition=attrs.composition,
                    subject_strength=attrs.subject_strength,
                    visual_appeal=attrs.visual_appeal,
                    sharpness=attrs.sharpness,
                    exposure_balance=attrs.exposure_balance,
                    noise_level=attrs.noise_level,
                    model_name=attrs.model_name,
                    model_version=attrs.model_version,
                ),
                explanation=explanation,
                improvements=improvements,
                description=description,
                cached=True,
            )
        except Exception:
            scores[image_path] = None

    return CachedScoreResponse(scores=scores)


@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    try:
        cache = Cache()
        if hasattr(cache, "get_stats"):
            return cache.get_stats()
        return {"total_entries": 0, "cache_size_bytes": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear")
async def clear_cache():
    """Clear the inference cache."""
    try:
        cache = Cache()
        if hasattr(cache, "clear"):
            cache.clear()
        return {"status": "cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
