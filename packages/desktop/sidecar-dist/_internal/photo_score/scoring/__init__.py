"""Scoring reducer and explanation generation.

This module provides scoring computation from normalized attributes
and explanation generation for photo critiques.

Main exports:
- ScoringReducer: Compute final scores from attributes
- ExplanationGenerator: Generate human-readable explanations
- CompositeScorer: Multi-model composite scoring system
- CompositeResult: Result container for composite scoring
"""

from photo_score.scoring.reducer import ScoringReducer
from photo_score.scoring.explanations import ExplanationGenerator
from photo_score.scoring.composite import CompositeScorer, CompositeResult

__all__ = [
    "ScoringReducer",
    "ExplanationGenerator",
    "CompositeScorer",
    "CompositeResult",
]
