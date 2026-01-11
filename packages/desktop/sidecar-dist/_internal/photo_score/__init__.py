"""Personal Photo Scoring CLI.

This package provides tools for scoring photo collections using vision models.

Main modules:
- inference: OpenRouter API client for vision model inference
- scoring: Score computation and explanation generation
- storage: SQLite cache for inference results
- ingestion: Image discovery and metadata extraction
- config: Configuration loading and validation
- output: CSV output generation
"""

__version__ = "0.1.0"

# Re-export commonly used classes for convenience
from photo_score.inference.client import OpenRouterClient, OpenRouterError
from photo_score.scoring.composite import CompositeScorer, CompositeResult
from photo_score.scoring.reducer import ScoringReducer
from photo_score.storage.cache import Cache
from photo_score.storage.models import NormalizedAttributes, ScoringResult

__all__ = [
    "__version__",
    "OpenRouterClient",
    "OpenRouterError",
    "CompositeScorer",
    "CompositeResult",
    "ScoringReducer",
    "Cache",
    "NormalizedAttributes",
    "ScoringResult",
]
