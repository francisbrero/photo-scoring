"""Triage handler for grid-based photo filtering on desktop."""

import base64
import io
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from PIL import Image
from PIL.ImageOps import exif_transpose

from photo_score.ingestion.discover import discover_images
from photo_score.triage.grid import GridGenerator

router = APIRouter()

# In-memory storage for triage jobs (desktop only handles one at a time)
_triage_jobs: dict[str, dict] = {}


class TriageConfig(BaseModel):
    """Configuration for a triage job."""

    directory: str = Field(..., description="Directory to scan for images")
    target: str = Field(
        default="10%", description="Selection target (e.g., '10%' or '50')"
    )
    criteria: str = Field(default="standout", description="Selection criteria")
    passes: int = Field(default=2, ge=1, le=2, description="Number of passes")


class TriageStartResponse(BaseModel):
    """Response when starting a triage job."""

    job_id: str
    status: str
    photo_count: int
    estimated_grids: int


class TriageProgress(BaseModel):
    """Progress information for a triage job."""

    phase: str
    current_step: int
    total_steps: int
    percentage: float
    message: str


class TriageStatusResponse(BaseModel):
    """Response for triage job status."""

    job_id: str
    status: str
    progress: Optional[TriageProgress]
    total_input: int
    pass1_survivors: int
    final_selected: int
    error_message: Optional[str]


class TriagePhoto(BaseModel):
    """A photo selected by triage."""

    image_id: str
    file_path: str
    filename: str
    thumbnail: Optional[str] = None  # base64 encoded


class TriageResultsResponse(BaseModel):
    """Response with triage results."""

    job_id: str
    status: str
    selected_photos: list[TriagePhoto]
    total_input: int
    pass1_survivors: int
    final_selected: int
    target: str
    criteria: str


def _calculate_credits(photo_count: int) -> int:
    """Calculate credits needed for triage."""
    if photo_count <= 100:
        return 1
    elif photo_count <= 500:
        return 3
    elif photo_count <= 1000:
        return 5
    elif photo_count <= 2000:
        return 8
    return 10


def _parse_target(target: str, total: int) -> int:
    """Parse target string to number of photos to select."""
    if target.endswith("%"):
        pct = float(target[:-1])
        return max(1, int(total * pct / 100))
    return int(target)


@router.post("/start", response_model=TriageStartResponse)
async def start_triage(config: TriageConfig, background_tasks: BackgroundTasks):
    """Start a local triage job.

    Desktop triage works by:
    1. Discovering images in the specified directory
    2. Generating grid composites locally
    3. Sending grids to the cloud API for analysis
    4. Mapping results back to local file paths
    """
    dir_path = Path(config.directory)

    if not dir_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Directory not found: {config.directory}"
        )

    if not dir_path.is_dir():
        raise HTTPException(
            status_code=400, detail=f"Path is not a directory: {config.directory}"
        )

    # Discover images
    records = discover_images(dir_path)

    if len(records) == 0:
        raise HTTPException(status_code=400, detail="No images found in directory")

    if len(records) > 2000:
        raise HTTPException(
            status_code=400,
            detail=f"Too many images ({len(records)}). Maximum is 2000.",
        )

    # Calculate estimated grids
    coarse_grids = (len(records) + 399) // 400  # 20x20 = 400 photos per grid
    fine_grids = (int(len(records) * 0.25) + 15) // 16  # Estimate 25% pass1, 4x4 = 16
    estimated_grids = coarse_grids + fine_grids if config.passes == 2 else coarse_grids

    # Create job
    job_id = str(uuid.uuid4())
    _triage_jobs[job_id] = {
        "status": "pending",
        "config": config.model_dump(),
        "records": [
            {
                "image_id": r.image_id,
                "file_path": str(r.file_path),
                "filename": r.filename,
            }
            for r in records
        ],
        "total_input": len(records),
        "pass1_survivors": 0,
        "final_selected": 0,
        "selected_ids": [],
        "error_message": None,
        "progress": {
            "phase": "preparing",
            "current_step": 0,
            "total_steps": estimated_grids,
            "percentage": 0,
            "message": "Preparing images...",
        },
    }

    # Start background processing
    background_tasks.add_task(run_triage_background, job_id)

    return TriageStartResponse(
        job_id=job_id,
        status="processing",
        photo_count=len(records),
        estimated_grids=estimated_grids,
    )


async def run_triage_background(job_id: str):
    """Run triage processing in background."""
    job = _triage_jobs.get(job_id)
    if not job:
        return

    try:
        job["status"] = "processing"
        config = job["config"]
        records = job["records"]
        total = len(records)

        # Parse target
        target_count = _parse_target(config["target"], total)

        # Initialize grid generator
        generator = GridGenerator()

        # --- Pass 1: Coarse (20x20) ---
        job["progress"]["phase"] = "coarse_pass"
        job["progress"]["message"] = "Running coarse pass..."

        # Create grid images for coarse pass
        coarse_size = 20
        coarse_grids = []
        file_paths = [Path(r["file_path"]) for r in records]

        # Generate grids
        grid_results = generator.generate_grids(file_paths)

        # Convert GridResult objects to (temp_file, paths) tuples
        for grid_result in grid_results:
            # Save grid to temp file
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".jpg", delete=False
            ) as f:
                grid_bytes = generator.grid_to_bytes(grid_result)
                f.write(grid_bytes)
                grid_path = f.name

            # Get the file paths that went into this grid
            chunk_paths = [
                str(grid_result.coord_to_path[coord])
                for coord in sorted(grid_result.coord_to_path.keys())
            ]
            coarse_grids.append((grid_path, chunk_paths))

        # Analyze grids via cloud API (uses user's credits)
        selected_paths_pass1 = set()

        # Get auth token
        from .auth import get_auth_token

        auth_token = get_auth_token()
        if not auth_token:
            raise RuntimeError("Not authenticated - please log in to use Triage")

        for idx, (grid_path, chunk_paths) in enumerate(coarse_grids):
            job["progress"]["current_step"] = idx + 1
            job["progress"]["percentage"] = (
                (idx + 1) / len(coarse_grids) * 50
                if config["passes"] == 2
                else (idx + 1) / len(coarse_grids) * 100
            )
            job["progress"]["message"] = (
                f"Coarse pass: analyzing grid {idx + 1}/{len(coarse_grids)}"
            )

            try:
                # Read grid image and encode as base64
                with open(grid_path, "rb") as f:
                    grid_data = base64.b64encode(f.read()).decode("utf-8")

                # Analyze grid via cloud API
                selected_coords = await analyze_grid_via_cloud(
                    grid_data,
                    "coarse",
                    config["criteria"],
                    config["target"],
                    len(all_paths),
                    auth_token,
                )

                # Map coordinates back to file paths
                grid_size = min(coarse_size, int(len(chunk_paths) ** 0.5) + 1)
                for coord in selected_coords:
                    row, col = coord
                    idx = row * grid_size + col
                    if idx < len(chunk_paths):
                        selected_paths_pass1.add(chunk_paths[idx])

            except Exception:
                # On error, keep all photos from this grid
                for p in chunk_paths:
                    selected_paths_pass1.add(p)
            finally:
                # Clean up grid file
                try:
                    os.unlink(grid_path)
                except Exception:
                    pass

        job["pass1_survivors"] = len(selected_paths_pass1)

        # --- Pass 2: Fine (4x4) if enabled ---
        if config["passes"] == 2 and len(selected_paths_pass1) > target_count:
            job["progress"]["phase"] = "fine_pass"
            job["progress"]["message"] = "Running fine pass..."

            fine_size = 4
            fine_grids = []
            pass1_list = [Path(p) for p in selected_paths_pass1]

            # Create fine-pass generator
            from photo_score.triage.grid import create_fine_grid_generator

            fine_generator = create_fine_grid_generator()

            # Generate grids
            grid_results = fine_generator.generate_grids(pass1_list)

            # Convert GridResult objects to (temp_file, paths) tuples
            for grid_result in grid_results:
                # Save grid to temp file
                with tempfile.NamedTemporaryFile(
                    mode="wb", suffix=".jpg", delete=False
                ) as f:
                    grid_bytes = fine_generator.grid_to_bytes(grid_result)
                    f.write(grid_bytes)
                    grid_path = f.name

                # Get the file paths that went into this grid
                chunk_paths = [
                    str(grid_result.coord_to_path[coord])
                    for coord in sorted(grid_result.coord_to_path.keys())
                ]
                fine_grids.append((grid_path, chunk_paths))

            selected_paths_final = set()
            for idx, (grid_path, chunk_paths) in enumerate(fine_grids):
                progress_base = 50
                job["progress"]["current_step"] = idx + 1
                job["progress"]["percentage"] = (
                    progress_base + (idx + 1) / len(fine_grids) * 50
                )
                job["progress"]["message"] = (
                    f"Fine pass: analyzing grid {idx + 1}/{len(fine_grids)}"
                )

                try:
                    # Read grid image and encode as base64
                    with open(grid_path, "rb") as f:
                        grid_data = base64.b64encode(f.read()).decode("utf-8")

                    # Analyze grid via cloud API
                    selected_coords = await analyze_grid_via_cloud(
                        grid_data,
                        "fine",
                        config["criteria"],
                        config["target"],
                        len(all_paths),
                        auth_token,
                    )

                    # Map coordinates back to file paths
                    grid_size = min(fine_size, int(len(chunk_paths) ** 0.5) + 1)
                    for coord in selected_coords:
                        row, col = coord
                        idx = row * grid_size + col
                        if idx < len(chunk_paths):
                            selected_paths_final.add(chunk_paths[idx])

                except Exception:
                    # On error, keep all photos from this grid
                    for p in chunk_paths:
                        selected_paths_final.add(p)
                finally:
                    # Clean up grid file
                    try:
                        os.unlink(grid_path)
                    except Exception:
                        pass

            selected_paths = selected_paths_final
        else:
            selected_paths = selected_paths_pass1

        # Map selected paths back to image IDs
        selected_ids = []
        for record in records:
            if record["file_path"] in selected_paths:
                selected_ids.append(record["image_id"])

        job["selected_ids"] = selected_ids
        job["final_selected"] = len(selected_ids)
        job["status"] = "completed"
        job["progress"]["phase"] = "complete"
        job["progress"]["percentage"] = 100
        job["progress"]["message"] = "Complete"

    except Exception as e:
        job["status"] = "failed"
        job["error_message"] = str(e)


async def analyze_grid_via_cloud(
    grid_base64: str,
    pass_type: str,
    criteria: str,
    target: str,
    photo_count: int,
    auth_token: str,
) -> list[tuple[int, int]]:
    """Analyze grid by calling cloud API (uses user's credits, not local API key)."""
    from .cloud_client import get_api_base_url

    api_url = get_api_base_url()

    payload = {
        "grid_base64": grid_base64,
        "pass_type": pass_type,
        "criteria": criteria,
        "target": target,
        "photo_count": photo_count,
    }

    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{api_url}/triage/analyze-grid",
            json=payload,
            headers=headers,
        )

        if response.status_code == 402:
            raise RuntimeError("Insufficient credits for triage")
        elif response.status_code == 401:
            raise RuntimeError("Not authenticated - please log in")
        elif response.status_code != 200:
            raise RuntimeError(f"API error {response.status_code}: {response.text}")

        result = response.json()
        return result["coordinates"]

    # If all models fail, return empty (conservative)
    return []


@router.get("/{job_id}/status", response_model=TriageStatusResponse)
async def get_triage_status(job_id: str):
    """Get the status of a triage job."""
    job = _triage_jobs.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Triage job not found")

    progress = None
    if job["status"] == "processing":
        prog = job.get("progress", {})
        progress = TriageProgress(
            phase=prog.get("phase", "processing"),
            current_step=prog.get("current_step", 0),
            total_steps=prog.get("total_steps", 1),
            percentage=prog.get("percentage", 0),
            message=prog.get("message", "Processing..."),
        )

    return TriageStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=progress,
        total_input=job.get("total_input", 0),
        pass1_survivors=job.get("pass1_survivors", 0),
        final_selected=job.get("final_selected", 0),
        error_message=job.get("error_message"),
    )


@router.get("/{job_id}/results", response_model=TriageResultsResponse)
async def get_triage_results(job_id: str):
    """Get the results of a completed triage job."""
    job = _triage_jobs.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Triage job not found")

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Triage not complete. Status: {job['status']}",
        )

    # Build selected photos list with thumbnails
    selected_ids = set(job.get("selected_ids", []))
    selected_photos = []

    for record in job["records"]:
        if record["image_id"] in selected_ids:
            # Generate thumbnail
            thumbnail = None
            try:
                file_path = Path(record["file_path"])
                if file_path.exists():
                    # Handle HEIC files
                    if file_path.suffix.lower() in (".heic", ".heif"):
                        import pillow_heif

                        pillow_heif.register_heif_opener()

                    with Image.open(file_path) as img:
                        img = exif_transpose(img)
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        img.thumbnail((200, 200), Image.Resampling.LANCZOS)

                        buffer = io.BytesIO()
                        img.save(buffer, format="JPEG", quality=80)
                        buffer.seek(0)
                        thumbnail = base64.b64encode(buffer.getvalue()).decode("utf-8")
            except Exception:
                pass

            selected_photos.append(
                TriagePhoto(
                    image_id=record["image_id"],
                    file_path=record["file_path"],
                    filename=record["filename"],
                    thumbnail=thumbnail,
                )
            )

    config = job.get("config", {})

    return TriageResultsResponse(
        job_id=job_id,
        status=job["status"],
        selected_photos=selected_photos,
        total_input=job.get("total_input", 0),
        pass1_survivors=job.get("pass1_survivors", 0),
        final_selected=job.get("final_selected", 0),
        target=config.get("target", "10%"),
        criteria=config.get("criteria", "standout"),
    )


@router.delete("/{job_id}")
async def cancel_triage(job_id: str):
    """Cancel a triage job."""
    job = _triage_jobs.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Triage job not found")

    job["status"] = "cancelled"

    # Remove from memory
    del _triage_jobs[job_id]

    return {"message": "Triage job cancelled"}


@router.post("/{job_id}/copy-selected")
async def copy_selected_photos(job_id: str, destination: str):
    """Copy selected photos to a destination directory."""
    import shutil

    job = _triage_jobs.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Triage job not found")

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail="Triage must be completed before copying",
        )

    dest_path = Path(destination)
    if not dest_path.exists():
        dest_path.mkdir(parents=True)

    selected_ids = set(job.get("selected_ids", []))
    copied = 0

    for record in job["records"]:
        if record["image_id"] in selected_ids:
            src = Path(record["file_path"])
            if src.exists():
                dst = dest_path / record["filename"]
                # Handle duplicates
                if dst.exists():
                    stem = dst.stem
                    suffix = dst.suffix
                    counter = 1
                    while dst.exists():
                        dst = dest_path / f"{stem}_{counter}{suffix}"
                        counter += 1
                shutil.copy2(src, dst)
                copied += 1

    return {"copied": copied, "destination": str(dest_path)}
