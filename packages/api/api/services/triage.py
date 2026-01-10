"""Triage service for grid-based photo filtering.

Uses the photo_score.triage module for grid generation and model inference.
"""

import base64
import io
import logging
import re
import uuid
from datetime import UTC, datetime

import httpx
from PIL import Image, ImageOps
from supabase import Client

from ..config import get_settings

logger = logging.getLogger(__name__)

# Try to import HEIC support
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    pass

# Grid settings
COARSE_GRID_SIZE = 20  # 20x20 = 400 photos per grid
FINE_GRID_SIZE = 4  # 4x4 = 16 photos per grid
THUMBNAIL_SIZE_COARSE = 100  # pixels
THUMBNAIL_SIZE_FINE = 400  # pixels

# Row labels for coordinate system
ROW_LABELS = "ABCDEFGHIJKLMNOPQRST"

# Models for triage (same as composite scoring)
TRIAGE_MODELS = [
    "qwen/qwen2.5-vl-72b-instruct",
    "google/gemini-2.5-flash",
]

# Coordinate pattern for parsing model responses
COORD_PATTERN = re.compile(r"\b([A-T])(\d{1,2})\b", re.IGNORECASE)

# API settings
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_IMAGE_DIMENSION = 2048


def calculate_triage_credits(photo_count: int) -> int:
    """Calculate credits needed for triage based on photo count.

    Triage is much cheaper than full scoring because it uses grid analysis
    instead of per-image inference.

    Args:
        photo_count: Number of photos to triage.

    Returns:
        Number of credits required.
    """
    if photo_count <= 100:
        return 1
    elif photo_count <= 500:
        return 3
    elif photo_count <= 1000:
        return 5
    elif photo_count <= 2000:
        return 8
    return 10


class TriageService:
    """Service for running grid-based photo triage."""

    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.settings = get_settings()
        self.http_client = httpx.Client(timeout=180.0)

    async def create_job(
        self,
        user_id: str,
        target: str = "10%",
        criteria: str = "standout",
        passes: int = 2,
        job_id: str | None = None,
    ) -> dict:
        """Create a new triage job.

        Args:
            user_id: The user's ID.
            target: Selection target (e.g., "10%" or "50").
            criteria: Selection criteria.
            passes: Number of passes (1 or 2).
            job_id: Optional pre-generated job ID (for client-side uploads).

        Returns:
            The created job record.
        """
        if job_id is None:
            job_id = str(uuid.uuid4())

        result = (
            self.supabase.table("triage_jobs")
            .insert(
                {
                    "id": job_id,
                    "user_id": user_id,
                    "status": "pending",
                    "target": target,
                    "criteria": criteria,
                    "passes": passes,
                    "phase": "uploading",
                }
            )
            .execute()
        )

        return result.data[0] if result.data else {"id": job_id}

    async def add_photo_to_job(
        self,
        job_id: str,
        original_filename: str,
        storage_path: str,
        image_hash: str | None = None,
        file_size: int | None = None,
    ) -> dict:
        """Add a photo to a triage job.

        Args:
            job_id: The triage job ID.
            original_filename: Original filename.
            storage_path: Path in Supabase storage.
            image_hash: SHA256 hash of image content.
            file_size: File size in bytes.

        Returns:
            The created photo record.
        """
        result = (
            self.supabase.table("triage_photos")
            .insert(
                {
                    "job_id": job_id,
                    "original_filename": original_filename,
                    "storage_path": storage_path,
                    "image_hash": image_hash,
                    "file_size": file_size,
                }
            )
            .execute()
        )

        return result.data[0] if result.data else {}

    async def update_job_status(
        self,
        job_id: str,
        status: str | None = None,
        phase: str | None = None,
        current_step: int | None = None,
        total_steps: int | None = None,
        error_message: str | None = None,
        **kwargs,
    ) -> None:
        """Update job status and progress.

        Args:
            job_id: The triage job ID.
            status: New status.
            phase: New phase.
            current_step: Current step number.
            total_steps: Total steps.
            error_message: Error message if failed.
            **kwargs: Additional fields to update.
        """
        updates = {}
        if status is not None:
            updates["status"] = status
        if phase is not None:
            updates["phase"] = phase
        if current_step is not None:
            updates["current_step"] = current_step
        if total_steps is not None:
            updates["total_steps"] = total_steps
        if error_message is not None:
            updates["error_message"] = error_message

        updates.update(kwargs)

        if updates:
            self.supabase.table("triage_jobs").update(updates).eq("id", job_id).execute()

    async def get_job(self, job_id: str, user_id: str) -> dict | None:
        """Get a triage job by ID.

        Args:
            job_id: The triage job ID.
            user_id: The user's ID (for authorization).

        Returns:
            The job record or None.
        """
        result = (
            self.supabase.table("triage_jobs")
            .select("*")
            .eq("id", job_id)
            .eq("user_id", user_id)
            .execute()
        )

        return result.data[0] if result.data else None

    async def get_active_jobs(self, user_id: str) -> list[dict]:
        """Get all active (pending or processing) triage jobs for a user.

        Args:
            user_id: The user's ID.

        Returns:
            List of active job records.
        """
        result = (
            self.supabase.table("triage_jobs")
            .select("*")
            .eq("user_id", user_id)
            .in_("status", ["pending", "processing"])
            .order("created_at", desc=True)
            .execute()
        )

        return result.data or []

    async def get_job_photos(self, job_id: str, selected_only: bool = False) -> list[dict]:
        """Get photos for a triage job.

        Args:
            job_id: The triage job ID.
            selected_only: If True, only return selected photos.

        Returns:
            List of photo records.
        """
        query = self.supabase.table("triage_photos").select("*").eq("job_id", job_id)

        if selected_only:
            query = query.eq("final_selected", True)

        result = query.order("created_at").execute()

        return result.data or []

    async def run_triage(self, job_id: str, user_id: str) -> dict:
        """Run the triage process for a job.

        This is the main processing function that:
        1. Processes photos grid-by-grid (memory efficient)
        2. Generates grids with downloaded images
        3. Sends grids to vision models for analysis
        4. Parses selections
        5. Updates photo records with results

        Memory optimization: Images are downloaded per-grid batch, not all at once.
        See ADR 011 for details.

        Args:
            job_id: The triage job ID.
            user_id: The user's ID.

        Returns:
            Job result with selection counts.
        """
        logger.info(f"[TRIAGE] Starting triage for job {job_id}")
        logger.info(f"[TRIAGE] Supabase URL: {self.settings.supabase_url}")
        try:
            # Get job and photos
            logger.info(f"[TRIAGE] Fetching job {job_id} for user {user_id}")
            job = await self.get_job(job_id, user_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")
            logger.info(f"[TRIAGE] Got job: {job.get('status')}, target={job.get('target')}")

            logger.info(f"[TRIAGE] Fetching photos for job {job_id}")
            photos = await self.get_job_photos(job_id)
            if not photos:
                raise ValueError("No photos in job")
            logger.info(f"[TRIAGE] Got {len(photos)} photos")

            total_photos = len(photos)
            target = job["target"]
            criteria = job["criteria"]
            passes = job.get("passes", 2)

            # Update job status
            await self.update_job_status(
                job_id,
                status="processing",
                phase="coarse_pass",
                total_input=total_photos,
                started_at=datetime.now(UTC).isoformat(),
            )

            # Calculate target percentage
            if target.endswith("%"):
                target_pct = float(target[:-1])
            else:
                target_count = int(target)
                target_pct = 100.0 * target_count / total_photos

            # Pass 1: Coarse selection with 20x20 grids
            # Images are downloaded per-grid to minimize memory usage

            # Be more permissive in coarse pass
            coarse_target_pct = min(target_pct * 2.5, 50.0)

            coarse_selected, coarse_grids, coarse_calls = await self._run_pass(
                job_id,
                photos,  # Pass photo records, not image data
                grid_size=COARSE_GRID_SIZE,
                thumbnail_size=THUMBNAIL_SIZE_COARSE,
                target_pct=coarse_target_pct,
                criteria=criteria,
                pass_name="coarse",
            )

            # Mark coarse selections
            for photo_id in coarse_selected:
                self.supabase.table("triage_photos").update({"selected_coarse": True}).eq(
                    "id", photo_id
                ).execute()

            logger.info(f"[TRIAGE] Coarse pass: {len(coarse_selected)}/{total_photos} selected")

            await self.update_job_status(job_id, pass1_survivors=len(coarse_selected))

            # Filter photos for fine pass
            fine_photos = [p for p in photos if p["id"] in coarse_selected]

            final_selected = coarse_selected
            fine_grids = 0
            fine_calls = 0

            if passes == 2 and len(fine_photos) > 0:
                # Pass 2: Fine selection with 4x4 grids
                await self.update_job_status(job_id, phase="fine_pass")

                # Adjust target for smaller pool
                fine_target_pct = target_pct * total_photos / len(fine_photos)

                fine_selected, fine_grids, fine_calls = await self._run_pass(
                    job_id,
                    fine_photos,  # Pass photo records, not image data
                    grid_size=FINE_GRID_SIZE,
                    thumbnail_size=THUMBNAIL_SIZE_FINE,
                    target_pct=fine_target_pct,
                    criteria=criteria,
                    pass_name="fine",
                )

                # Mark fine selections
                for photo_id in fine_selected:
                    self.supabase.table("triage_photos").update({"selected_fine": True}).eq(
                        "id", photo_id
                    ).execute()

                final_selected = fine_selected
                logger.info(f"[TRIAGE] Fine pass: {len(fine_selected)}/{len(fine_photos)} selected")

            # Trim to exact target
            target_count = max(1, int(total_photos * target_pct / 100))
            if len(final_selected) > target_count:
                final_selected = set(list(final_selected)[:target_count])

            # Mark final selections
            for photo_id in final_selected:
                self.supabase.table("triage_photos").update({"final_selected": True}).eq(
                    "id", photo_id
                ).execute()

            # Update job as complete
            await self.update_job_status(
                job_id,
                status="completed",
                phase="complete",
                final_selected=len(final_selected),
                grids_processed=coarse_grids + fine_grids,
                api_calls=coarse_calls + fine_calls,
                completed_at=datetime.now(UTC).isoformat(),
            )

            return {
                "total_input": total_photos,
                "pass1_survivors": len(coarse_selected),
                "final_selected": len(final_selected),
                "grids_processed": coarse_grids + fine_grids,
                "api_calls": coarse_calls + fine_calls,
            }

        except Exception as e:
            logger.exception(f"[TRIAGE] FAILED for job {job_id}: {e}")
            await self.update_job_status(job_id, status="failed", error_message=str(e))
            raise

    def _download_and_thumbnail(
        self, photo: dict, thumbnail_size: int
    ) -> tuple[str, Image.Image] | None:
        """Download a single image and create thumbnail immediately.

        Memory optimization: Downloads one image at a time, creates thumbnail,
        then discards raw bytes. Only the small thumbnail stays in memory.
        See ADR 011 for details.

        Args:
            photo: Photo record with storage_path.
            thumbnail_size: Target thumbnail size in pixels.

        Returns:
            Tuple of (photo_id, thumbnail_image) or None on failure.
        """
        try:
            storage_path = photo["storage_path"]
            logger.debug(f"[TRIAGE] Downloading: {storage_path}")
            # Download from Supabase storage
            raw_bytes = self.supabase.storage.from_("photos").download(storage_path)
            logger.debug(f"[TRIAGE] Downloaded {len(raw_bytes)} bytes")

            # Immediately create thumbnail (discards raw_bytes after)
            thumbnail = self._create_thumbnail(raw_bytes, thumbnail_size)
            logger.debug(f"[TRIAGE] Created thumbnail {thumbnail.size}")

            # raw_bytes goes out of scope here and can be garbage collected
            return (photo["id"], thumbnail)
        except Exception as e:
            logger.error(
                f"[TRIAGE] Failed to download/thumbnail {photo.get('storage_path', 'unknown')}: {e}"
            )
            import traceback

            logger.error(traceback.format_exc())
            return None

    def _download_thumbnails_streaming(
        self, photos: list[dict], thumbnail_size: int
    ) -> dict[str, Image.Image]:
        """Download images and create thumbnails one at a time.

        Memory optimization: Only one raw image is in memory at a time.
        Thumbnails are small (~100x100 or ~400x400 pixels) so they fit easily.
        For 16 photos: ~16 * 100KB = 1.6MB instead of 16 * 3MB = 48MB.
        See ADR 011 for details.

        Args:
            photos: List of photo records to process.
            thumbnail_size: Target thumbnail size in pixels.

        Returns:
            Dict mapping photo ID to PIL Image thumbnail.
        """
        import gc

        thumbnails = {}
        for i, photo in enumerate(photos):
            result = self._download_and_thumbnail(photo, thumbnail_size)
            if result:
                photo_id, thumbnail = result
                thumbnails[photo_id] = thumbnail

            # Force garbage collection every 4 images to keep memory low
            if (i + 1) % 4 == 0:
                gc.collect()

        return thumbnails

    async def _run_pass(
        self,
        job_id: str,
        photos: list[dict],
        grid_size: int,
        thumbnail_size: int,
        target_pct: float,
        criteria: str,
        pass_name: str,
    ) -> tuple[set[str], int, int]:
        """Run a single triage pass.

        Memory optimization: Downloads images one at a time, creates thumbnails
        immediately, and only keeps small thumbnails in memory.
        For 16 photos at 100x100 thumbnails: ~1.6MB instead of 48MB raw images.
        See ADR 011 for details.

        Args:
            job_id: The triage job ID.
            photos: List of photo records (not image data).
            grid_size: Grid dimension (e.g., 20 for 20x20).
            thumbnail_size: Thumbnail size in pixels.
            target_pct: Target selection percentage.
            criteria: Selection criteria.
            pass_name: "coarse" or "fine".

        Returns:
            Tuple of (selected_photo_ids, grids_processed, api_calls).
        """
        import gc

        photos_per_grid = grid_size * grid_size
        num_grids = (len(photos) + photos_per_grid - 1) // photos_per_grid

        selected_ids: set[str] = set()
        api_calls = 0

        for grid_idx in range(num_grids):
            start = grid_idx * photos_per_grid
            end = min(start + photos_per_grid, len(photos))
            batch_photos = photos[start:end]

            logger.info(
                f"[TRIAGE] Grid {grid_idx + 1}/{num_grids}: downloading {len(batch_photos)} photos"
            )

            # Download images ONE AT A TIME and create thumbnails (memory optimization)
            # Only thumbnails stay in memory, raw image bytes are discarded immediately
            thumbnails = self._download_thumbnails_streaming(batch_photos, thumbnail_size)

            logger.info(
                f"[TRIAGE] Grid {grid_idx + 1}/{num_grids}: created {len(thumbnails)} thumbnails"
            )

            if not thumbnails:
                logger.warning(f"No thumbnails created for grid {grid_idx + 1}")
                continue

            # Generate grid image from thumbnails (no raw image data needed)
            grid_image, coord_to_id = self._generate_grid_from_thumbnails(
                thumbnails, grid_size, thumbnail_size
            )

            # Clear thumbnails to free memory before API call
            thumbnails.clear()
            gc.collect()

            # Build prompt
            rows = min(grid_size, (len(batch_photos) + grid_size - 1) // grid_size)
            cols = min(grid_size, len(batch_photos))
            last_row = ROW_LABELS[rows - 1]
            coord_range = f"A1-{last_row}{cols}"

            prompt = self._build_prompt(
                rows=rows,
                cols=cols,
                coord_range=coord_range,
                total_photos=len(batch_photos),
                target_pct=target_pct,
                criteria=criteria,
                pass_name=pass_name,
            )

            logger.info(f"[TRIAGE] Grid {grid_idx + 1}/{num_grids}: querying vision models")

            # Query models (union consensus)
            union_coords: set[str] = set()
            for model_id in TRIAGE_MODELS:
                try:
                    coords = await self._query_model(grid_image, prompt, model_id)
                    union_coords.update(coords)
                    api_calls += 1
                except Exception as e:
                    logger.warning(f"Model {model_id} failed: {e}")
                    api_calls += 1

            # Map coordinates to photo IDs
            for coord in union_coords:
                coord_upper = coord.upper()
                if coord_upper in coord_to_id:
                    selected_ids.add(coord_to_id[coord_upper])

            # Update progress
            await self.update_job_status(job_id, current_step=grid_idx + 1, total_steps=num_grids)

            # Explicit cleanup to help garbage collector
            del grid_image
            del coord_to_id
            gc.collect()

        return selected_ids, num_grids, api_calls

    def _generate_grid_from_thumbnails(
        self,
        thumbnails: dict[str, Image.Image],
        grid_size: int,
        thumbnail_size: int,
    ) -> tuple[bytes, dict[str, str]]:
        """Generate a labeled grid image from pre-created thumbnails.

        Memory optimization: Takes PIL Image thumbnails directly instead of
        raw bytes, avoiding the need to hold raw image data in memory.
        See ADR 011 for details.

        Args:
            thumbnails: Dict mapping photo ID to PIL Image thumbnail.
            grid_size: Grid dimension.
            thumbnail_size: Thumbnail size in pixels.

        Returns:
            Tuple of (grid_jpeg_bytes, coord_to_photo_id_mapping).
        """
        from PIL import ImageDraw, ImageFont

        photo_ids = list(thumbnails.keys())
        num_photos = len(photo_ids)

        # Calculate actual dimensions
        cols = min(grid_size, num_photos)
        rows = (num_photos + cols - 1) // cols

        # Layout constants
        label_height = 20
        margin = 2
        row_label_width = 25
        col_label_height = 20
        background_color = (40, 40, 40)
        label_color = (255, 255, 0)

        cell_width = thumbnail_size + margin
        cell_height = thumbnail_size + label_height + margin

        img_width = row_label_width + (cols * cell_width)
        img_height = col_label_height + (rows * cell_height)

        # Create grid image
        grid_image = Image.new("RGB", (img_width, img_height), background_color)
        draw = ImageDraw.Draw(grid_image)

        # Try to load a font
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except OSError:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
            except OSError:
                font = ImageFont.load_default()

        # Draw column labels
        for col in range(cols):
            x = row_label_width + (col * cell_width) + (cell_width // 2)
            label = str(col + 1)
            bbox = draw.textbbox((0, 0), label, font=font)
            text_width = bbox[2] - bbox[0]
            draw.text((x - text_width // 2, 4), label, fill=label_color, font=font)

        # Draw thumbnails and labels
        coord_to_id: dict[str, str] = {}

        for idx, photo_id in enumerate(photo_ids):
            row = idx // cols
            col = idx % cols

            # Row label
            if col == 0:
                y = col_label_height + (row * cell_height) + (cell_height // 2)
                draw.text((5, y - 6), ROW_LABELS[row], fill=label_color, font=font)

            # Position
            x = row_label_width + (col * cell_width)
            y = col_label_height + (row * cell_height)

            # Paste pre-created thumbnail
            try:
                thumbnail = thumbnails[photo_id]
                grid_image.paste(thumbnail, (x, y))
            except Exception as e:
                logger.warning(f"Failed to paste thumbnail: {e}")
                draw.rectangle(
                    [x, y, x + thumbnail_size, y + thumbnail_size],
                    fill=(80, 80, 80),
                    outline=(120, 120, 120),
                )

            # Coordinate label
            coord = f"{ROW_LABELS[row]}{col + 1}"
            coord_to_id[coord] = photo_id

            label_y = y + thumbnail_size + 2
            bbox = draw.textbbox((0, 0), coord, font=font)
            text_width = bbox[2] - bbox[0]
            label_x = x + (thumbnail_size - text_width) // 2
            draw.text((label_x, label_y), coord, fill=label_color, font=font)

        # Convert to JPEG bytes
        buffer = io.BytesIO()
        grid_image.save(buffer, format="JPEG", quality=90)
        return buffer.getvalue(), coord_to_id

    def _generate_grid(
        self,
        images_data: dict[str, bytes],
        grid_size: int,
        thumbnail_size: int,
    ) -> tuple[bytes, dict[str, str]]:
        """Generate a labeled grid image (legacy method, kept for compatibility).

        Args:
            images_data: Dict mapping photo ID to image bytes.
            grid_size: Grid dimension.
            thumbnail_size: Thumbnail size in pixels.

        Returns:
            Tuple of (grid_jpeg_bytes, coord_to_photo_id_mapping).
        """
        photo_ids = list(images_data.keys())
        num_photos = len(photo_ids)

        # Calculate actual dimensions
        cols = min(grid_size, num_photos)
        rows = (num_photos + cols - 1) // cols

        # Layout constants
        label_height = 20
        margin = 2
        row_label_width = 25
        col_label_height = 20
        background_color = (40, 40, 40)
        label_color = (255, 255, 0)

        cell_width = thumbnail_size + margin
        cell_height = thumbnail_size + label_height + margin

        img_width = row_label_width + (cols * cell_width)
        img_height = col_label_height + (rows * cell_height)

        # Create grid image
        from PIL import ImageDraw, ImageFont

        grid_image = Image.new("RGB", (img_width, img_height), background_color)
        draw = ImageDraw.Draw(grid_image)

        # Try to load a font
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        except OSError:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            except OSError:
                font = ImageFont.load_default()

        # Draw column labels
        for col in range(cols):
            x = row_label_width + (col * cell_width) + (cell_width // 2)
            label = str(col + 1)
            bbox = draw.textbbox((0, 0), label, font=font)
            text_width = bbox[2] - bbox[0]
            draw.text((x - text_width // 2, 4), label, fill=label_color, font=font)

        # Draw thumbnails and labels
        coord_to_id: dict[str, str] = {}

        for idx, photo_id in enumerate(photo_ids):
            row = idx // cols
            col = idx % cols

            # Row label
            if col == 0:
                y = col_label_height + (row * cell_height) + (cell_height // 2)
                draw.text((5, y - 6), ROW_LABELS[row], fill=label_color, font=font)

            # Position
            x = row_label_width + (col * cell_width)
            y = col_label_height + (row * cell_height)

            # Load and paste thumbnail
            try:
                img_bytes = images_data[photo_id]
                thumbnail = self._create_thumbnail(img_bytes, thumbnail_size)
                grid_image.paste(thumbnail, (x, y))
            except Exception as e:
                logger.warning(f"Failed to create thumbnail: {e}")
                draw.rectangle(
                    [x, y, x + thumbnail_size, y + thumbnail_size],
                    fill=(80, 80, 80),
                    outline=(120, 120, 120),
                )

            # Coordinate label
            coord = f"{ROW_LABELS[row]}{col + 1}"
            coord_to_id[coord] = photo_id

            label_y = y + thumbnail_size + 2
            bbox = draw.textbbox((0, 0), coord, font=font)
            text_width = bbox[2] - bbox[0]
            label_x = x + (thumbnail_size - text_width) // 2
            draw.text((label_x, label_y), coord, fill=label_color, font=font)

        # Convert to JPEG bytes
        buffer = io.BytesIO()
        grid_image.save(buffer, format="JPEG", quality=90)
        return buffer.getvalue(), coord_to_id

    def _create_thumbnail(self, img_bytes: bytes, size: int) -> Image.Image:
        """Create a square thumbnail from image bytes.

        Args:
            img_bytes: Image file bytes.
            size: Target thumbnail size.

        Returns:
            PIL Image thumbnail.
        """
        with Image.open(io.BytesIO(img_bytes)) as img:
            # Apply EXIF orientation
            img = ImageOps.exif_transpose(img)

            # Convert to RGB
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            # Center crop to square
            width, height = img.size
            min_dim = min(width, height)
            left = (width - min_dim) // 2
            top = (height - min_dim) // 2
            img = img.crop((left, top, left + min_dim, top + min_dim))

            # Resize
            img = img.resize((size, size), Image.Resampling.LANCZOS)

            return img.copy()

    def _build_prompt(
        self,
        rows: int,
        cols: int,
        coord_range: str,
        total_photos: int,
        target_pct: float,
        criteria: str,
        pass_name: str,
    ) -> str:
        """Build the triage prompt.

        Args:
            rows: Number of rows in grid.
            cols: Number of columns.
            coord_range: Coordinate range string.
            total_photos: Total photos in grid.
            target_pct: Target selection percentage.
            criteria: Selection criteria.
            pass_name: "coarse" or "fine".

        Returns:
            Formatted prompt string.
        """
        target_count = max(1, int(total_photos * target_pct / 100))

        # Criteria descriptions
        if criteria.lower() == "standout":
            criteria_desc = """photos that stand out and catch the eye. Look for:
- Memorable moments and compelling subjects
- Strong composition and visual impact
- Interesting lighting or dramatic scenes
- Emotional resonance or storytelling
- Unique perspectives or creative framing"""
        elif criteria.lower() == "quality":
            criteria_desc = """photos with the best overall quality. Evaluate:
- Technical excellence (sharpness, exposure, focus)
- Strong composition and visual balance
- Good lighting and color
- Clear subject with appropriate depth of field
- Professional-level execution"""
        else:
            criteria_desc = criteria

        if pass_name == "coarse":
            return f"""You are a professional photo editor reviewing a grid of photos \
to identify the best candidates from a large collection.

The grid shows {total_photos} photos arranged in {rows} rows and {cols} columns.
Photos are labeled with coordinates from {coord_range} (row letter + column number).

YOUR TASK: Select {criteria_desc}

TARGET: Select approximately {target_pct:.0f}% of the photos (around {target_count} photos).

IMPORTANT GUIDELINES:
1. For groups of similar/duplicate photos (burst shots, same scene), select ONLY the best
2. Be selective - this is a triage pass to find the standout photos
3. Consider the photo's potential even at thumbnail size
4. Skip obviously flawed photos (blurry, badly exposed, uninteresting subjects)

RESPONSE FORMAT:
Return ONLY a comma-separated list of coordinates for selected photos.
Example: A1, A5, B3, C12, D7, E20

Do not include any explanation or other text. Just the coordinates."""
        else:
            return f"""You are a professional photo editor doing a detailed review \
of photo candidates.

The grid shows {total_photos} photos arranged in {rows} rows and {cols} columns.
Photos are labeled with coordinates from {coord_range}.

These photos passed an initial screening. Now evaluate them more carefully.

YOUR TASK: Select {criteria_desc}

TARGET: Select approximately {target_pct:.0f}% of these photos (around {target_count} photos).

DETAILED EVALUATION:
1. Look more carefully at composition, lighting, and subject matter
2. Consider technical quality: sharpness, exposure, color balance
3. For remaining similar photos, pick only the absolute best
4. Be more selective than the first pass - these should be the top picks

RESPONSE FORMAT:
Return ONLY a comma-separated list of coordinates for your final selections.
Example: A1, A3, B2, C4

Do not include any explanation or other text. Just the coordinates."""

    async def _query_model(self, grid_image_bytes: bytes, prompt: str, model_id: str) -> set[str]:
        """Query a vision model with a grid image.

        Args:
            grid_image_bytes: JPEG bytes of the grid.
            prompt: The prompt text.
            model_id: OpenRouter model ID.

        Returns:
            Set of selected coordinates.
        """
        base64_data = base64.b64encode(grid_image_bytes).decode("utf-8")

        payload = {
            "model": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_data}"},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "max_tokens": 1024,
            "temperature": 0,
        }

        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }

        response = self.http_client.post(OPENROUTER_API_URL, json=payload, headers=headers)

        if response.status_code != 200:
            raise RuntimeError(f"API error {response.status_code}: {response.text}")

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        # Parse coordinates
        coords = set()
        matches = COORD_PATTERN.findall(content)
        for row_letter, col_num in matches:
            coords.add(f"{row_letter.upper()}{col_num}")

        return coords

    def close(self):
        """Close the HTTP client."""
        self.http_client.close()
