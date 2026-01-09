"""Triage router for grid-based photo filtering."""

import hashlib
import io
import uuid
import zipfile
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..dependencies import CurrentUser, SupabaseClient
from ..services.credits import CreditService, InsufficientCreditsError
from ..services.triage import TriageService, calculate_triage_credits

router = APIRouter()

# Allowed image types
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/heic", "image/heif", "image/webp"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_PHOTOS = 2000


# --- Response Models ---


class TriageProgress(BaseModel):
    """Progress information for a triage job."""

    phase: str
    current_step: int
    total_steps: int
    percentage: float
    message: str


class TriageStartResponse(BaseModel):
    """Response when starting a triage job."""

    job_id: str
    status: str
    photo_count: int
    credits_deducted: int
    estimated_grids: int


class TriageStatusResponse(BaseModel):
    """Response for triage job status."""

    job_id: str
    status: str
    progress: TriageProgress | None
    total_input: int
    pass1_survivors: int
    final_selected: int
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class SelectedPhoto(BaseModel):
    """A photo selected by triage."""

    id: str
    original_filename: str
    storage_path: str
    thumbnail_url: str | None = None


class TriageResultsResponse(BaseModel):
    """Response with triage results."""

    job_id: str
    status: str
    selected_photos: list[SelectedPhoto]
    total_input: int
    pass1_survivors: int
    final_selected: int
    target: str
    criteria: str


class ProceedResponse(BaseModel):
    """Response when proceeding to full scoring."""

    queued_count: int
    credits_deducted: int


# --- Endpoints ---


class ActiveJobSummary(BaseModel):
    """Summary of an active triage job."""

    job_id: str
    status: str
    total_input: int
    progress_percentage: float
    phase: str
    created_at: datetime


class ActiveJobsResponse(BaseModel):
    """Response listing active triage jobs."""

    jobs: list[ActiveJobSummary]


@router.get("/active", response_model=ActiveJobsResponse)
async def get_active_jobs(
    user: CurrentUser,
    supabase: SupabaseClient,
):
    """Get all active (pending or processing) triage jobs for the current user.

    Returns:
        List of active job summaries.
    """
    triage_service = TriageService(supabase)
    jobs = await triage_service.get_active_jobs(user.id)

    summaries = []
    for job in jobs:
        current = job.get("current_step", 0)
        total = job.get("total_steps", 1)
        percentage = (current / total * 100) if total > 0 else 0

        summaries.append(
            ActiveJobSummary(
                job_id=job["id"],
                status=job["status"],
                total_input=job.get("total_input", 0),
                progress_percentage=percentage,
                phase=job.get("phase", "pending"),
                created_at=job["created_at"],
            )
        )

    return ActiveJobsResponse(jobs=summaries)


@router.post("/start", response_model=TriageStartResponse)
async def start_triage(
    user: CurrentUser,
    supabase: SupabaseClient,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    target: str = Form(default="10%"),
    criteria: str = Form(default="standout"),
    passes: int = Form(default=2),
):
    """Start a triage job with uploaded images.

    Uploads images to temporary storage, deducts credits, and starts
    background processing.

    Args:
        files: List of image files to triage.
        target: Selection target (e.g., "10%" or "50").
        criteria: Selection criteria ("standout", "quality", or custom).
        passes: Number of passes (1 or 2).

    Returns:
        Job ID and status information.
    """
    # Validate file count
    if len(files) > MAX_PHOTOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_PHOTOS} photos allowed per triage",
        )

    if len(files) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided",
        )

    # Validate passes
    if passes not in (1, 2):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passes must be 1 or 2",
        )

    # Calculate and check credits
    credits_needed = calculate_triage_credits(len(files))
    credit_service = CreditService(supabase)

    try:
        await credit_service.deduct_credit(user.id, credits_needed)
    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits: need {e.required}, have {e.available}",
        )

    # Create triage job
    triage_service = TriageService(supabase)
    job = await triage_service.create_job(
        user_id=user.id,
        target=target,
        criteria=criteria,
        passes=passes,
    )
    job_id = job["id"]

    # Upload files to storage and create photo records
    uploaded_count = 0
    for file in files:
        # Validate file type
        content_type = file.content_type or ""
        if content_type not in ALLOWED_TYPES:
            # Skip invalid files
            continue

        # Read file content
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            continue

        # Compute hash for deduplication
        image_hash = hashlib.sha256(content).hexdigest()

        # Generate storage path
        file_ext = file.filename.split(".")[-1] if file.filename else "jpg"
        storage_path = f"triage/{user.id}/{job_id}/{uuid.uuid4()}.{file_ext}"

        # Upload to Supabase storage
        try:
            supabase.storage.from_("photos").upload(
                storage_path,
                content,
                {"content-type": content_type},
            )
        except Exception:
            # Log but continue with other files
            continue

        # Create photo record
        await triage_service.add_photo_to_job(
            job_id=job_id,
            original_filename=file.filename or "unknown",
            storage_path=storage_path,
            image_hash=image_hash,
            file_size=len(content),
        )
        uploaded_count += 1

    if uploaded_count == 0:
        # Refund credits if no files uploaded
        await credit_service.refund_credit(user.id, credits_needed)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid images uploaded",
        )

    # Update job with photo count and credits
    await triage_service.update_job_status(
        job_id,
        total_input=uploaded_count,
        credits_deducted=credits_needed,
    )

    # Calculate estimated grids
    coarse_grids = (uploaded_count + 399) // 400  # 20x20 = 400
    fine_grids = (int(uploaded_count * 0.25) + 15) // 16  # Estimate 25% pass1, 4x4 = 16
    estimated_grids = coarse_grids + fine_grids if passes == 2 else coarse_grids

    # Start background processing
    background_tasks.add_task(run_triage_background, supabase, job_id, user.id, credits_needed)

    return TriageStartResponse(
        job_id=job_id,
        status="processing",
        photo_count=uploaded_count,
        credits_deducted=credits_needed,
        estimated_grids=estimated_grids,
    )


async def run_triage_background(
    supabase: SupabaseClient,
    job_id: str,
    user_id: str,
    credits_deducted: int,
):
    """Background task to run triage processing."""
    triage_service = TriageService(supabase)
    credit_service = CreditService(supabase)

    try:
        await triage_service.run_triage(job_id, user_id)
    except Exception:
        # Refund credits on failure
        try:
            await credit_service.refund_credit(user_id, credits_deducted)
        except Exception:
            pass  # Best effort refund
    finally:
        triage_service.close()


@router.get("/{job_id}/status", response_model=TriageStatusResponse)
async def get_triage_status(
    job_id: str,
    user: CurrentUser,
    supabase: SupabaseClient,
):
    """Get the status of a triage job.

    Args:
        job_id: The triage job ID.

    Returns:
        Current status and progress information.
    """
    triage_service = TriageService(supabase)
    job = await triage_service.get_job(job_id, user.id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Triage job not found",
        )

    # Build progress info
    progress = None
    if job["status"] == "processing":
        current = job.get("current_step", 0)
        total = job.get("total_steps", 1)
        phase = job.get("phase", "processing")

        phase_messages = {
            "uploading": "Uploading photos...",
            "grid_generation": "Generating grids...",
            "coarse_pass": f"Coarse selection: grid {current}/{total}",
            "fine_pass": f"Fine selection: grid {current}/{total}",
            "complete": "Complete",
        }

        progress = TriageProgress(
            phase=phase,
            current_step=current,
            total_steps=total,
            percentage=(current / total * 100) if total > 0 else 0,
            message=phase_messages.get(phase, "Processing..."),
        )

    return TriageStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=progress,
        total_input=job.get("total_input", 0),
        pass1_survivors=job.get("pass1_survivors", 0),
        final_selected=job.get("final_selected", 0),
        error_message=job.get("error_message"),
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
    )


@router.get("/{job_id}/results", response_model=TriageResultsResponse)
async def get_triage_results(
    job_id: str,
    user: CurrentUser,
    supabase: SupabaseClient,
):
    """Get the results of a completed triage job.

    Args:
        job_id: The triage job ID.

    Returns:
        List of selected photos with metadata.
    """
    triage_service = TriageService(supabase)
    job = await triage_service.get_job(job_id, user.id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Triage job not found",
        )

    if job["status"] not in ("completed", "failed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Triage not complete. Status: {job['status']}",
        )

    # Get selected photos
    photos = await triage_service.get_job_photos(job_id, selected_only=True)

    # Generate signed URLs for thumbnails
    selected_photos = []
    for photo in photos:
        # Generate signed URL (valid for 1 hour)
        try:
            url_result = supabase.storage.from_("photos").create_signed_url(
                photo["storage_path"], 3600
            )
            thumbnail_url = url_result.get("signedURL") or url_result.get("signedUrl")
        except Exception:
            thumbnail_url = None

        selected_photos.append(
            SelectedPhoto(
                id=photo["id"],
                original_filename=photo["original_filename"],
                storage_path=photo["storage_path"],
                thumbnail_url=thumbnail_url,
            )
        )

    return TriageResultsResponse(
        job_id=job_id,
        status=job["status"],
        selected_photos=selected_photos,
        total_input=job.get("total_input", 0),
        pass1_survivors=job.get("pass1_survivors", 0),
        final_selected=job.get("final_selected", 0),
        target=job.get("target", "10%"),
        criteria=job.get("criteria", "standout"),
    )


@router.post("/{job_id}/proceed", response_model=ProceedResponse)
async def proceed_to_scoring(
    job_id: str,
    user: CurrentUser,
    supabase: SupabaseClient,
    photo_ids: list[str] | None = None,
):
    """Queue selected photos for full scoring.

    Args:
        job_id: The triage job ID.
        photo_ids: Optional list of specific photo IDs to score.
                  If not provided, all selected photos are queued.

    Returns:
        Number of photos queued and credits deducted.
    """
    triage_service = TriageService(supabase)
    job = await triage_service.get_job(job_id, user.id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Triage job not found",
        )

    if job["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Triage must be completed before proceeding to scoring",
        )

    # Get photos to score
    photos = await triage_service.get_job_photos(job_id, selected_only=True)

    if photo_ids:
        photos = [p for p in photos if p["id"] in photo_ids]

    if not photos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No photos to score",
        )

    # Check credits (1 credit per photo for full scoring)
    credits_needed = len(photos)
    credit_service = CreditService(supabase)

    try:
        await credit_service.deduct_credit(user.id, credits_needed)
    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits: need {e.required}, have {e.available}",
        )

    # Move photos to scored_photos table and queue for scoring
    queued_count = 0
    for photo in photos:
        try:
            # Create scored_photos record
            photo_id = str(uuid.uuid4())
            supabase.table("scored_photos").insert(
                {
                    "id": photo_id,
                    "user_id": user.id,
                    "image_path": photo["storage_path"],
                    "original_filename": photo["original_filename"],
                    "image_hash": photo.get("image_hash"),
                }
            ).execute()

            # Queue for scoring
            supabase.table("scoring_queue").insert(
                {
                    "user_id": user.id,
                    "photo_id": photo_id,
                    "status": "pending",
                }
            ).execute()

            queued_count += 1
        except Exception:
            continue

    # Refund unused credits
    if queued_count < credits_needed:
        await credit_service.refund_credit(user.id, credits_needed - queued_count)

    return ProceedResponse(
        queued_count=queued_count,
        credits_deducted=queued_count,
    )


@router.get("/{job_id}/download")
async def download_selected(
    job_id: str,
    user: CurrentUser,
    supabase: SupabaseClient,
):
    """Download selected photos as a ZIP file.

    Args:
        job_id: The triage job ID.

    Returns:
        ZIP file containing selected photos.
    """
    triage_service = TriageService(supabase)
    job = await triage_service.get_job(job_id, user.id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Triage job not found",
        )

    if job["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Triage must be completed before downloading",
        )

    # Get selected photos
    photos = await triage_service.get_job_photos(job_id, selected_only=True)

    if not photos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No photos to download",
        )

    # Create ZIP file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for photo in photos:
            try:
                # Download from storage
                content = supabase.storage.from_("photos").download(photo["storage_path"])
                # Add to ZIP with original filename
                zip_file.writestr(photo["original_filename"], content)
            except Exception:
                continue

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=triage_{job_id[:8]}_selected.zip"},
    )


@router.delete("/{job_id}")
async def cancel_triage(
    job_id: str,
    user: CurrentUser,
    supabase: SupabaseClient,
):
    """Cancel a triage job and clean up resources.

    Args:
        job_id: The triage job ID.

    Returns:
        Success message.
    """
    triage_service = TriageService(supabase)
    job = await triage_service.get_job(job_id, user.id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Triage job not found",
        )

    # Update status to cancelled
    await triage_service.update_job_status(job_id, status="cancelled")

    # Clean up storage (photos will be auto-deleted by cascade)
    photos = await triage_service.get_job_photos(job_id)
    for photo in photos:
        try:
            supabase.storage.from_("photos").remove([photo["storage_path"]])
        except Exception:
            pass

    # Delete job (cascade deletes photos)
    supabase.table("triage_jobs").delete().eq("id", job_id).execute()

    return {"message": "Triage job cancelled and cleaned up"}
