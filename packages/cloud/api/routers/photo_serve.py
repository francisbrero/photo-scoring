"""Router for serving photo images at /photos/:path.

This is a separate router to handle the /photos/{path} endpoint that the
frontend expects for loading images. It requires authentication to verify
the user has access to the photo.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse

from ..dependencies import CurrentUser, SupabaseClient

router = APIRouter()


@router.get("/{path:path}")
async def serve_photo(
    path: str,
    user: CurrentUser,
    supabase: SupabaseClient,
):
    """Serve a photo image by its storage path.

    This endpoint is used by the frontend to serve images.
    The path should match the image_path returned from GET /api/photos.

    Returns a redirect to a signed Supabase Storage URL (valid for 1 hour).
    """
    # Verify the photo belongs to the user by checking the database
    result = (
        supabase.table("scored_photos")
        .select("id")
        .eq("storage_path", path)
        .eq("user_id", user.id)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found or access denied",
        )

    # Generate signed URL (valid for 1 hour)
    try:
        signed_url_response = supabase.storage.from_("photos").create_signed_url(
            path, expires_in=3600
        )

        if not signed_url_response or "signedURL" not in signed_url_response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate signed URL",
            )

        return RedirectResponse(
            url=signed_url_response["signedURL"],
            status_code=status.HTTP_302_FOUND,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage error: {str(e)}",
        ) from e
