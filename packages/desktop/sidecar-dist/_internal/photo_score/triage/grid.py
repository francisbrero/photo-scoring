"""Grid image generation for visual triage.

Creates composite grid images with coordinate labels for vision model evaluation.
"""

import io
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

logger = logging.getLogger(__name__)

# Try to import HEIC support
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False
    logger.debug("pillow_heif not installed, HEIC support disabled")


# Grid coordinate labels (A-T for rows, 1-20 for columns)
ROW_LABELS = "ABCDEFGHIJKLMNOPQRST"


@dataclass
class GridResult:
    """Result of grid generation."""

    grid_image: Image.Image
    """The composite grid image."""

    coord_to_path: dict[str, Path]
    """Mapping from coordinate (e.g., 'A1') to original file path."""

    rows: int
    """Number of rows in the grid."""

    cols: int
    """Number of columns in the grid."""

    thumbnail_size: int
    """Size of each thumbnail in pixels."""

    @property
    def coord_range(self) -> str:
        """Human-readable coordinate range (e.g., 'A1-T20')."""
        last_row = ROW_LABELS[self.rows - 1]
        return f"A1-{last_row}{self.cols}"

    @property
    def total_photos(self) -> int:
        """Total number of photos in this grid."""
        return len(self.coord_to_path)


@dataclass
class GridGenerator:
    """Generates labeled grid images from photo collections."""

    grid_size: int = 20
    """Number of rows/columns in the grid (default: 20x20 = 400 photos)."""

    thumbnail_size: int = 100
    """Size of each thumbnail in pixels."""

    label_height: int = 20
    """Height reserved for coordinate labels."""

    margin: int = 2
    """Margin between thumbnails."""

    background_color: tuple[int, int, int] = (40, 40, 40)
    """Background color (dark gray)."""

    label_color: tuple[int, int, int] = (255, 255, 0)
    """Label text color (yellow for visibility)."""

    _font: ImageFont.FreeTypeFont | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize font for labels."""
        # Try to load a readable font, fall back to default
        try:
            self._font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        except (OSError, IOError):
            try:
                self._font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12
                )
            except (OSError, IOError):
                self._font = ImageFont.load_default()

    def generate_grids(self, image_paths: list[Path]) -> list[GridResult]:
        """Generate grid images from a list of photo paths.

        Args:
            image_paths: List of paths to images.

        Returns:
            List of GridResult objects, one per grid needed.
        """
        if not image_paths:
            return []

        photos_per_grid = self.grid_size * self.grid_size
        num_grids = math.ceil(len(image_paths) / photos_per_grid)

        grids = []
        for grid_idx in range(num_grids):
            start_idx = grid_idx * photos_per_grid
            end_idx = min(start_idx + photos_per_grid, len(image_paths))
            batch = image_paths[start_idx:end_idx]

            grid_result = self._generate_single_grid(batch)
            grids.append(grid_result)
            logger.info(
                f"Generated grid {grid_idx + 1}/{num_grids} "
                f"with {grid_result.total_photos} photos"
            )

        return grids

    def _generate_single_grid(self, image_paths: list[Path]) -> GridResult:
        """Generate a single grid image from photos.

        Args:
            image_paths: List of paths (up to grid_size^2).

        Returns:
            GridResult with the composite image and coordinate mapping.
        """
        num_photos = len(image_paths)

        # Calculate actual grid dimensions (may be smaller than max)
        cols = min(self.grid_size, num_photos)
        rows = math.ceil(num_photos / cols)

        # Recalculate cols for last row optimization
        if rows == 1:
            cols = num_photos
        else:
            cols = self.grid_size

        # Calculate image dimensions
        cell_width = self.thumbnail_size + self.margin
        cell_height = self.thumbnail_size + self.label_height + self.margin

        # Add space for row labels on left and column labels on top
        row_label_width = 25
        col_label_height = 20

        img_width = row_label_width + (cols * cell_width)
        img_height = col_label_height + (rows * cell_height)

        # Create the composite image
        grid_image = Image.new("RGB", (img_width, img_height), self.background_color)
        draw = ImageDraw.Draw(grid_image)

        # Draw column labels (1, 2, 3, ...)
        for col in range(cols):
            x = row_label_width + (col * cell_width) + (cell_width // 2)
            label = str(col + 1)
            bbox = draw.textbbox((0, 0), label, font=self._font)
            text_width = bbox[2] - bbox[0]
            draw.text(
                (x - text_width // 2, 4), label, fill=self.label_color, font=self._font
            )

        # Draw row labels and thumbnails
        coord_to_path: dict[str, Path] = {}

        for idx, image_path in enumerate(image_paths):
            row = idx // cols
            col = idx % cols

            # Row label
            row_label = ROW_LABELS[row]
            if col == 0:
                y = col_label_height + (row * cell_height) + (cell_height // 2)
                draw.text((5, y - 6), row_label, fill=self.label_color, font=self._font)

            # Calculate position
            x = row_label_width + (col * cell_width)
            y = col_label_height + (row * cell_height)

            # Load and resize thumbnail
            try:
                thumbnail = self._load_thumbnail(image_path)
                grid_image.paste(thumbnail, (x, y))
            except Exception as e:
                logger.warning(f"Failed to load {image_path}: {e}")
                # Draw placeholder
                draw.rectangle(
                    [x, y, x + self.thumbnail_size, y + self.thumbnail_size],
                    fill=(80, 80, 80),
                    outline=(120, 120, 120),
                )

            # Store coordinate mapping
            coord = f"{row_label}{col + 1}"
            coord_to_path[coord] = image_path

            # Draw coordinate label below thumbnail
            label_y = y + self.thumbnail_size + 2
            bbox = draw.textbbox((0, 0), coord, font=self._font)
            text_width = bbox[2] - bbox[0]
            label_x = x + (self.thumbnail_size - text_width) // 2
            draw.text((label_x, label_y), coord, fill=self.label_color, font=self._font)

        return GridResult(
            grid_image=grid_image,
            coord_to_path=coord_to_path,
            rows=rows,
            cols=cols,
            thumbnail_size=self.thumbnail_size,
        )

    def _load_thumbnail(self, image_path: Path) -> Image.Image:
        """Load an image and create a square thumbnail.

        Args:
            image_path: Path to the image file.

        Returns:
            Square thumbnail image.
        """
        with Image.open(image_path) as img:
            # Apply EXIF orientation
            img = ImageOps.exif_transpose(img)

            # Convert to RGB if needed
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            # Create square crop from center
            width, height = img.size
            min_dim = min(width, height)
            left = (width - min_dim) // 2
            top = (height - min_dim) // 2
            right = left + min_dim
            bottom = top + min_dim
            img = img.crop((left, top, right, bottom))

            # Resize to thumbnail size
            img = img.resize(
                (self.thumbnail_size, self.thumbnail_size), Image.Resampling.LANCZOS
            )

            return img.copy()

    def grid_to_bytes(self, grid_result: GridResult, quality: int = 85) -> bytes:
        """Convert grid image to JPEG bytes for API submission.

        Args:
            grid_result: The grid result containing the image.
            quality: JPEG quality (0-100).

        Returns:
            JPEG image bytes.
        """
        buffer = io.BytesIO()
        grid_result.grid_image.save(buffer, format="JPEG", quality=quality)
        return buffer.getvalue()


def create_fine_grid_generator() -> GridGenerator:
    """Create a generator configured for fine-pass 4x4 grids.

    Returns:
        GridGenerator with 4x4 grid size and larger thumbnails.
    """
    return GridGenerator(
        grid_size=4,
        thumbnail_size=400,  # Larger thumbnails for detail
        label_height=25,
        margin=4,
    )
