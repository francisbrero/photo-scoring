"""Triage-specific prompts for grid-based photo selection."""

# Criteria presets
CRITERIA_STANDOUT = "standout"
CRITERIA_QUALITY = "quality"

STANDOUT_DESCRIPTION = """photos that stand out and catch the eye. Look for:
- Memorable moments and compelling subjects
- Strong composition and visual impact
- Interesting lighting or dramatic scenes
- Emotional resonance or storytelling
- Unique perspectives or creative framing"""

QUALITY_DESCRIPTION = """photos with the best overall quality. Evaluate:
- Technical excellence (sharpness, exposure, focus)
- Strong composition and visual balance
- Good lighting and color
- Clear subject with appropriate depth of field
- Professional-level execution"""


def get_criteria_description(criteria: str) -> str:
    """Get the description for a criteria preset or return custom text.

    Args:
        criteria: Either 'standout', 'quality', or custom text.

    Returns:
        The criteria description to use in the prompt.
    """
    if criteria.lower() == CRITERIA_STANDOUT:
        return STANDOUT_DESCRIPTION
    elif criteria.lower() == CRITERIA_QUALITY:
        return QUALITY_DESCRIPTION
    else:
        # Custom criteria provided by user
        return criteria


COARSE_TRIAGE_PROMPT = """You are a professional photo editor reviewing a grid of photos to identify the best candidates from a large collection.

The grid shows {total_photos} photos arranged in {rows} rows and {cols} columns.
Photos are labeled with coordinates from {coord_range} (row letter + column number).

YOUR TASK: Select {criteria_description}

TARGET: Select approximately {target_percentage}% of the photos (around {target_count} photos).

IMPORTANT GUIDELINES:
1. For groups of similar or duplicate photos (burst shots, same scene), select ONLY the single best one
2. Be selective - this is a triage pass to find the standout photos
3. Consider the photo's potential even at thumbnail size
4. Skip obviously flawed photos (blurry, badly exposed, uninteresting subjects)

RESPONSE FORMAT:
Return ONLY a comma-separated list of coordinates for selected photos.
Example: A1, A5, B3, C12, D7, E20

Do not include any explanation or other text. Just the coordinates."""


FINE_TRIAGE_PROMPT = """You are a professional photo editor doing a detailed review of photo candidates.

The grid shows {total_photos} photos arranged in {rows} rows and {cols} columns.
Photos are labeled with coordinates from {coord_range}.

These photos passed an initial screening. Now evaluate them more carefully.

YOUR TASK: Select {criteria_description}

TARGET: Select approximately {target_percentage}% of these photos (around {target_count} photos).

DETAILED EVALUATION:
1. Look more carefully at composition, lighting, and subject matter
2. Consider technical quality: sharpness, exposure, color balance
3. For remaining similar photos, pick only the absolute best
4. Be more selective than the first pass - these should be the top picks

RESPONSE FORMAT:
Return ONLY a comma-separated list of coordinates for your final selections.
Example: A1, A3, B2, C4

Do not include any explanation or other text. Just the coordinates."""


def build_coarse_prompt(
    rows: int,
    cols: int,
    coord_range: str,
    total_photos: int,
    target_percentage: float,
    criteria: str,
) -> str:
    """Build the prompt for coarse (20x20) grid triage.

    Args:
        rows: Number of rows in the grid.
        cols: Number of columns in the grid.
        coord_range: Coordinate range string (e.g., 'A1-T20').
        total_photos: Total number of photos in the grid.
        target_percentage: Target percentage to select (e.g., 20.0 for 20%).
        criteria: Criteria preset ('standout', 'quality') or custom text.

    Returns:
        Formatted prompt string.
    """
    target_count = max(1, int(total_photos * target_percentage / 100))
    criteria_description = get_criteria_description(criteria)

    return COARSE_TRIAGE_PROMPT.format(
        rows=rows,
        cols=cols,
        coord_range=coord_range,
        total_photos=total_photos,
        target_percentage=target_percentage,
        target_count=target_count,
        criteria_description=criteria_description,
    )


def build_fine_prompt(
    rows: int,
    cols: int,
    coord_range: str,
    total_photos: int,
    target_percentage: float,
    criteria: str,
) -> str:
    """Build the prompt for fine (4x4) grid triage.

    Args:
        rows: Number of rows in the grid.
        cols: Number of columns in the grid.
        coord_range: Coordinate range string (e.g., 'A1-D4').
        total_photos: Total number of photos in the grid.
        target_percentage: Target percentage to select.
        criteria: Criteria preset or custom text.

    Returns:
        Formatted prompt string.
    """
    target_count = max(1, int(total_photos * target_percentage / 100))
    criteria_description = get_criteria_description(criteria)

    return FINE_TRIAGE_PROMPT.format(
        rows=rows,
        cols=cols,
        coord_range=coord_range,
        total_photos=total_photos,
        target_percentage=target_percentage,
        target_count=target_count,
        criteria_description=criteria_description,
    )
