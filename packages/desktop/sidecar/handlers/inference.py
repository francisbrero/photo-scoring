"""Inference and scoring handlers."""

import asyncio
import os
from pathlib import Path
from typing import Optional

# Get root path for config files
ROOT_PATH = Path(__file__).parent.parent.parent.parent.parent
DEFAULT_CONFIG = ROOT_PATH / "configs" / "default.yaml"

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
    improvements: list[str] = []
    description: str = ""
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

        # Variables for critique data (from fresh inference)
        critique_explanation = ""
        improvements: list[str] = []
        description = ""

        if attrs is None:
            # Need to run inference - run in thread pool to not block event loop
            from photo_score.scoring.composite import CompositeScorer

            def run_scoring():
                scorer = CompositeScorer()
                return scorer.score_image(file_path)

            # Run blocking inference in a thread pool
            result = await asyncio.to_thread(run_scoring)

            # CompositeResult has weighted scores directly on the object
            attrs = NormalizedAttributes(
                image_id=image_id,
                composition=result.composition,
                subject_strength=result.subject_strength,
                visual_appeal=result.visual_appeal,
                sharpness=result.sharpness,
                exposure_balance=result.exposure,
                noise_level=result.noise_level,
            )
            cache.store_attributes(attrs)

            # Capture critique data from CompositeResult
            critique_explanation = result.explanation
            improvements = result.improvements
            description = result.description

            # Store critique in cache for future retrieval
            cache.store_critique(
                image_id,
                description=description,
                explanation=critique_explanation,
                improvements=improvements,
            )
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


class RegenerateCritiqueRequest(BaseModel):
    """Request to regenerate critique for images with cached attributes."""

    image_paths: list[str]


class RegenerateCritiqueResponse(BaseModel):
    """Response for critique regeneration."""

    regenerated: int
    skipped: int
    errors: int


@router.post("/regenerate-critiques", response_model=RegenerateCritiqueResponse)
async def regenerate_critiques(request: RegenerateCritiqueRequest):
    """Regenerate critiques for images that have attributes but no critique.

    This makes API calls only for the critique generation, not full inference.
    """
    from photo_score.scoring.composite import CompositeScorer, CompositeResult, FeatureExtraction

    regenerated = 0
    skipped = 0
    errors = 0

    # Check for API key
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise HTTPException(
            status_code=400,
            detail="OPENROUTER_API_KEY not set.",
        )

    scorer = CompositeScorer()

    def generate_critique_for_image(file_path: Path, image_id: str, attrs) -> dict | None:
        """Generate critique for a single image."""
        # Build a minimal CompositeResult for critique generation
        result = CompositeResult(
            image_path=str(file_path.name),
            features=FeatureExtraction(),
            composition=attrs.composition,
            subject_strength=attrs.subject_strength,
            visual_appeal=attrs.visual_appeal,
            sharpness=attrs.sharpness,
            exposure=attrs.exposure_balance,
            noise_level=attrs.noise_level,
            aesthetic_score=(attrs.composition * 0.4 + attrs.subject_strength * 0.35 + attrs.visual_appeal * 0.25),
            technical_score=(attrs.sharpness * 0.4 + attrs.exposure_balance * 0.35 + attrs.noise_level * 0.25),
        )
        result.final_score = (result.aesthetic_score * 0.6 + result.technical_score * 0.4) * 100

        critique = scorer.generate_critique(file_path, result)
        return {
            "description": "",  # Would need metadata call
            "explanation": scorer.format_explanation(critique),
            "improvements": scorer.format_improvements(critique),
        }

    for image_path in request.image_paths:
        file_path = Path(image_path)
        if not file_path.exists():
            errors += 1
            continue

        try:
            image_id = compute_image_id(file_path)
            cache = Cache()

            # Check if already has critique
            if cache.has_critique(image_id):
                skipped += 1
                continue

            # Check if has attributes (needed for critique context)
            attrs = cache.get_attributes(image_id)
            if attrs is None:
                skipped += 1
                continue

            # Generate critique in thread pool
            critique_data = await asyncio.to_thread(
                generate_critique_for_image, file_path, image_id, attrs
            )

            if critique_data:
                cache.store_critique(
                    image_id,
                    description=critique_data["description"],
                    explanation=critique_data["explanation"],
                    improvements=critique_data["improvements"],
                )
                regenerated += 1
            else:
                errors += 1

        except Exception as e:
            print(f"Error regenerating critique for {image_path}: {e}")
            errors += 1

    scorer.close()

    return RegenerateCritiqueResponse(
        regenerated=regenerated,
        skipped=skipped,
        errors=errors,
    )


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
