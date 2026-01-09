"""Grid-based visual triage for large photo collections.

This module provides fast, cost-effective filtering of large photo collections
using composite grid images evaluated by vision models.

Key components:
- GridGenerator: Creates labeled grid images from photo collections
- TriageSelector: Multi-model selection with union consensus
- create_selection_folder: Symlink output creation
"""

from photo_score.triage.grid import GridGenerator, GridResult
from photo_score.triage.selector import TriageSelector, TriageResult
from photo_score.triage.output import create_selection_folder

__all__ = [
    "GridGenerator",
    "GridResult",
    "TriageSelector",
    "TriageResult",
    "create_selection_folder",
]
