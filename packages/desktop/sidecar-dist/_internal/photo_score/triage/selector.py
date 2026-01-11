"""Multi-model triage selector with union consensus.

Evaluates grid images using multiple vision models and combines selections.
"""

import base64
import io
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from photo_score.inference.client import OpenRouterClient

from photo_score.triage.grid import (
    GridGenerator,
    GridResult,
    create_fine_grid_generator,
)
from photo_score.triage.prompts import build_coarse_prompt, build_fine_prompt

logger = logging.getLogger(__name__)

# Models for triage (same as composite scoring for consistency)
TRIAGE_MODELS = [
    "qwen/qwen2.5-vl-72b-instruct",  # ~$0.0002/call
    "google/gemini-2.5-flash",  # ~$0.0008/call
]

# Coordinate pattern: A-T followed by 1-20
COORD_PATTERN = re.compile(r"\b([A-T])(\d{1,2})\b", re.IGNORECASE)


@dataclass
class ModelSelection:
    """Selection result from a single model."""

    model_id: str
    coordinates: set[str]
    raw_response: str
    success: bool = True
    error: str = ""


@dataclass
class GridSelectionResult:
    """Combined selection result for a grid."""

    grid_index: int
    model_selections: list[ModelSelection]
    union_coordinates: set[str]
    """Coordinates selected by ANY model (union consensus)."""

    selected_paths: list[Path]
    """Paths to selected photos."""


@dataclass
class TriageResult:
    """Final result of triage process."""

    total_input: int
    """Total number of input photos."""

    pass1_survivors: int
    """Number of photos after coarse pass."""

    final_selected: int
    """Number of photos after fine pass."""

    selected_paths: list[Path]
    """Paths to final selected photos."""

    grids_processed: int
    """Total number of grids processed."""

    api_calls: int
    """Total number of API calls made."""


@dataclass
class TriageSelector:
    """Multi-model triage selector with union consensus."""

    api_key: str | None = None
    models: list[str] = field(default_factory=lambda: TRIAGE_MODELS.copy())
    coarse_grid_size: int = 20
    fine_grid_size: int = 4

    _client: "OpenRouterClient | None" = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize the OpenRouter client."""
        from photo_score.inference.client import OpenRouterClient

        self._client = OpenRouterClient(api_key=self.api_key)

    def run_triage(
        self,
        image_paths: list[Path],
        target: str,
        criteria: str = "standout",
        passes: int = 2,
    ) -> TriageResult:
        """Run the full triage process.

        Args:
            image_paths: List of paths to photos.
            target: Target selection, either percentage ("10%") or count ("50").
            criteria: Selection criteria ('standout', 'quality', or custom text).
            passes: Number of passes (1 = coarse only, 2 = coarse + fine).

        Returns:
            TriageResult with selected photo paths.
        """
        if not image_paths:
            return TriageResult(
                total_input=0,
                pass1_survivors=0,
                final_selected=0,
                selected_paths=[],
                grids_processed=0,
                api_calls=0,
            )

        total_input = len(image_paths)
        target_percentage = self._parse_target(target, total_input)

        logger.info(
            f"Starting triage: {total_input} photos, target {target_percentage:.1f}%, "
            f"criteria='{criteria}', passes={passes}"
        )

        # Pass 1: Coarse selection with 20x20 grids
        coarse_generator = GridGenerator(
            grid_size=self.coarse_grid_size,
            thumbnail_size=100,
        )

        # For coarse pass, we want to be more permissive (keep ~30-40% as buffer)
        coarse_target = min(target_percentage * 2.5, 50.0)

        pass1_selected, pass1_grids, pass1_calls = self._run_pass(
            image_paths=image_paths,
            generator=coarse_generator,
            target_percentage=coarse_target,
            criteria=criteria,
            pass_name="coarse",
            prompt_builder=build_coarse_prompt,
        )

        logger.info(
            f"Pass 1 complete: {len(pass1_selected)}/{total_input} photos "
            f"({100 * len(pass1_selected) / total_input:.1f}%) survived"
        )

        if passes == 1 or len(pass1_selected) == 0:
            # Single pass or nothing survived
            final_selected = self._trim_to_target(
                pass1_selected, target_percentage, total_input
            )
            return TriageResult(
                total_input=total_input,
                pass1_survivors=len(pass1_selected),
                final_selected=len(final_selected),
                selected_paths=final_selected,
                grids_processed=pass1_grids,
                api_calls=pass1_calls,
            )

        # Pass 2: Fine selection with 4x4 grids
        fine_generator = create_fine_grid_generator()

        pass2_selected, pass2_grids, pass2_calls = self._run_pass(
            image_paths=pass1_selected,
            generator=fine_generator,
            target_percentage=target_percentage
            * total_input
            / len(pass1_selected),  # Adjust for smaller pool
            criteria=criteria,
            pass_name="fine",
            prompt_builder=build_fine_prompt,
        )

        logger.info(
            f"Pass 2 complete: {len(pass2_selected)}/{len(pass1_selected)} photos "
            f"({100 * len(pass2_selected) / len(pass1_selected):.1f}%) selected"
        )

        # Trim to exact target
        final_selected = self._trim_to_target(
            pass2_selected, target_percentage, total_input
        )

        return TriageResult(
            total_input=total_input,
            pass1_survivors=len(pass1_selected),
            final_selected=len(final_selected),
            selected_paths=final_selected,
            grids_processed=pass1_grids + pass2_grids,
            api_calls=pass1_calls + pass2_calls,
        )

    def _run_pass(
        self,
        image_paths: list[Path],
        generator: GridGenerator,
        target_percentage: float,
        criteria: str,
        pass_name: str,
        prompt_builder: callable,
    ) -> tuple[list[Path], int, int]:
        """Run a single triage pass.

        Args:
            image_paths: Paths to process.
            generator: Grid generator to use.
            target_percentage: Target percentage for this pass.
            criteria: Selection criteria.
            pass_name: Name for logging.
            prompt_builder: Function to build prompts.

        Returns:
            Tuple of (selected_paths, grids_processed, api_calls).
        """
        grids = generator.generate_grids(image_paths)
        selected_paths: list[Path] = []
        api_calls = 0

        for grid_idx, grid in enumerate(grids):
            logger.info(
                f"{pass_name.capitalize()} pass: Processing grid {grid_idx + 1}/{len(grids)} "
                f"({grid.total_photos} photos)"
            )

            # Build prompt
            prompt = prompt_builder(
                rows=grid.rows,
                cols=grid.cols,
                coord_range=grid.coord_range,
                total_photos=grid.total_photos,
                target_percentage=target_percentage,
                criteria=criteria,
            )

            # Query each model
            union_coords: set[str] = set()
            for model_id in self.models:
                try:
                    coords = self._query_model(grid, prompt, model_id)
                    union_coords.update(coords)
                    api_calls += 1
                    logger.debug(f"{model_id} selected {len(coords)} photos")
                except Exception as e:
                    logger.warning(f"Model {model_id} failed on grid {grid_idx}: {e}")
                    api_calls += 1  # Still count failed calls

            # Map coordinates to paths
            for coord in union_coords:
                coord_upper = coord.upper()
                if coord_upper in grid.coord_to_path:
                    selected_paths.append(grid.coord_to_path[coord_upper])

        return selected_paths, len(grids), api_calls

    def _query_model(self, grid: GridResult, prompt: str, model_id: str) -> set[str]:
        """Query a model with a grid image.

        Args:
            grid: The grid to evaluate.
            prompt: The prompt to use.
            model_id: The model to query.

        Returns:
            Set of selected coordinates.
        """
        # Convert grid to base64
        buffer = io.BytesIO()
        grid.grid_image.save(buffer, format="JPEG", quality=90)
        base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # Make API call

        payload = {
            "model": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_data}"
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "max_tokens": 1024,  # More tokens for coordinate lists
            "temperature": 0,
        }

        headers = {
            "Authorization": f"Bearer {self._client.api_key}",
            "Content-Type": "application/json",
        }

        response = self._client.client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers=headers,
        )

        if response.status_code != 200:
            raise RuntimeError(f"API error {response.status_code}: {response.text}")

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        # Parse coordinates from response
        return self._parse_coordinates(content, grid)

    def _parse_coordinates(self, response: str, grid: GridResult) -> set[str]:
        """Parse coordinate strings from model response.

        Args:
            response: Raw model response text.
            grid: The grid (for validation).

        Returns:
            Set of valid coordinates.
        """
        coords = set()

        # Find all coordinate patterns
        matches = COORD_PATTERN.findall(response)
        for row_letter, col_num in matches:
            coord = f"{row_letter.upper()}{col_num}"
            # Validate coordinate exists in this grid
            if coord in grid.coord_to_path:
                coords.add(coord)

        return coords

    def _parse_target(self, target: str, total: int) -> float:
        """Parse target string to percentage.

        Args:
            target: Either "10%" or "50" (absolute count).
            total: Total number of photos.

        Returns:
            Target as percentage (0-100).
        """
        target = target.strip()
        if target.endswith("%"):
            return float(target[:-1])
        else:
            count = int(target)
            return 100.0 * count / total

    def _trim_to_target(
        self, paths: list[Path], target_percentage: float, total: int
    ) -> list[Path]:
        """Trim selection to match target.

        Args:
            paths: Current selected paths.
            target_percentage: Target as percentage.
            total: Original total (for percentage calculation).

        Returns:
            Trimmed list of paths.
        """
        target_count = max(1, int(total * target_percentage / 100))
        if len(paths) <= target_count:
            return paths
        return paths[:target_count]

    def close(self) -> None:
        """Close the client."""
        if self._client:
            self._client.close()

    def __enter__(self) -> "TriageSelector":
        return self

    def __exit__(self, *args) -> None:
        self.close()
