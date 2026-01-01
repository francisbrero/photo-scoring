"""Inference and scoring handlers."""

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from photo_score.ingestion.discover import compute_image_id
from photo_score.storage.cache import Cache
from photo_score.storage.models import NormalizedAttributes
from photo_score.config.loader import load_config
from photo_score.scoring.reducer import ScoringReducer
from photo_score.scoring.explanations import ExplanationGenerator

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
    cached: bool


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
    """Score a single image."""
    file_path = Path(request.image_path)

    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Image not found: {request.image_path}"
        )

    # Check for API key
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise HTTPException(
            status_code=400,
            detail="OPENROUTER_API_KEY not set. Please configure your API key.",
        )

    try:
        image_id = compute_image_id(file_path)
        cache = Cache()
        cached = False

        # Check cache first
        attrs = cache.get_attributes(image_id)

        if attrs is None:
            # Need to run inference
            from photo_score.scoring.composite import CompositeScorer

            scorer = CompositeScorer()
            result = scorer.score_image(file_path)

            attrs = NormalizedAttributes(
                image_id=image_id,
                composition=result.aesthetic_scores.composition,
                subject_strength=result.aesthetic_scores.subject_strength,
                visual_appeal=result.aesthetic_scores.visual_appeal,
                sharpness=result.technical_scores.sharpness,
                exposure_balance=result.technical_scores.exposure_balance,
                noise_level=result.technical_scores.noise_level,
            )
            cache.store_attributes(attrs)
        else:
            cached = True

        # Load config and compute score
        config_path = request.config_path or "configs/default.yaml"
        config = load_config(Path(config_path))
        reducer = ScoringReducer(config)
        score_result = reducer.compute_scores(image_id, str(file_path), attrs)

        # Generate explanation
        explainer = ExplanationGenerator(config)
        explanation = explainer.generate(score_result)

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
            cached=cached,
        )
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
        config_path = request.config_path or "configs/default.yaml"
        config = load_config(Path(config_path))
        reducer = ScoringReducer(config)
        score_result = reducer.compute_scores(image_id, str(file_path), attrs)

        # Generate explanation
        explainer = ExplanationGenerator(config)
        explanation = explainer.generate(score_result)

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
