"""Cloud API client for inference."""

import base64
import os

import httpx

CLOUD_API_URL = os.environ.get(
    "PHOTO_SCORE_API_URL", "https://photo-score-api.onrender.com"
)


class CloudInferenceError(Exception):
    """Raised when cloud inference fails."""

    def __init__(self, message: str, status_code: int = 500, retryable: bool = False):
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        super().__init__(message)


class InsufficientCreditsError(CloudInferenceError):
    """Raised when user has insufficient credits."""

    def __init__(self, message: str = "Insufficient credits. Please purchase more."):
        super().__init__(message, status_code=402, retryable=False)


class AuthenticationError(CloudInferenceError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Not authenticated. Please log in."):
        super().__init__(message, status_code=401, retryable=False)


def get_auth_token() -> str | None:
    """Get auth token from settings file."""
    from .auth import get_auth_token as _get_auth_token

    return _get_auth_token()


async def score_image(image_path: str, image_hash: str) -> dict:
    """Score an image using the cloud API.

    Uses /api/inference/analyze for full scoring pipeline including
    attributes, features, critique, and metadata.

    Args:
        image_path: Path to the image file
        image_hash: SHA256 hash of the image

    Returns:
        Dictionary with full scoring results:
        - attributes (composition, subject_strength, etc.)
        - scores (final_score, aesthetic_score, technical_score)
        - critique (explanation, improvements, description)
        - credits_remaining, cached

    Raises:
        CloudInferenceError: If inference fails
        InsufficientCreditsError: If user has no credits
        AuthenticationError: If user is not authenticated
    """
    token = get_auth_token()
    if not token:
        raise AuthenticationError()

    # Read and encode image
    with open(image_path, "rb") as f:
        image_data = f.read()
    image_base64 = base64.b64encode(image_data).decode("utf-8")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CLOUD_API_URL}/api/inference/analyze",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "image_data": image_base64,
                    "image_hash": image_hash,
                },
                timeout=180.0,  # Full pipeline can take a while
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise AuthenticationError("Session expired. Please log in again.")
            elif response.status_code == 402:
                raise InsufficientCreditsError()
            elif response.status_code == 429:
                raise CloudInferenceError(
                    "Rate limit exceeded. Please try again later.",
                    status_code=429,
                    retryable=True,
                )
            else:
                try:
                    detail = response.json().get("detail", "Scoring failed")
                except Exception:
                    detail = response.text or "Scoring failed"
                raise CloudInferenceError(detail, status_code=response.status_code)

    except httpx.TimeoutException:
        raise CloudInferenceError(
            "Request timed out. Please try again.",
            status_code=504,
            retryable=True,
        )
    except httpx.RequestError as e:
        raise CloudInferenceError(
            f"Cannot connect to Photo Scorer service: {str(e)}",
            status_code=503,
            retryable=True,
        )


# Keep old function name as alias for backwards compatibility
async def analyze_image(image_path: str, image_hash: str) -> dict:
    """Deprecated: Use score_image instead."""
    return await score_image(image_path, image_hash)


async def extract_metadata(image_path: str, image_hash: str) -> dict:
    """Extract metadata from an image using the cloud API.

    Args:
        image_path: Path to the image file
        image_hash: SHA256 hash of the image

    Returns:
        Dictionary with description and location

    Raises:
        CloudInferenceError: If metadata extraction fails
        InsufficientCreditsError: If user has no credits
        AuthenticationError: If user is not authenticated
    """
    token = get_auth_token()
    if not token:
        raise AuthenticationError()

    # Read and encode image
    with open(image_path, "rb") as f:
        image_data = f.read()
    image_base64 = base64.b64encode(image_data).decode("utf-8")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CLOUD_API_URL}/api/inference/metadata",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "image_data": image_base64,
                    "image_hash": image_hash,
                },
                timeout=60.0,
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise AuthenticationError("Session expired. Please log in again.")
            elif response.status_code == 402:
                raise InsufficientCreditsError()
            elif response.status_code == 429:
                raise CloudInferenceError(
                    "Rate limit exceeded. Please try again later.",
                    status_code=429,
                    retryable=True,
                )
            else:
                detail = response.json().get("detail", "Metadata extraction failed")
                raise CloudInferenceError(detail, status_code=response.status_code)

    except httpx.TimeoutException:
        raise CloudInferenceError(
            "Request timed out. Please try again.",
            status_code=504,
            retryable=True,
        )
    except httpx.RequestError as e:
        raise CloudInferenceError(
            f"Cannot connect to Photo Scorer service: {str(e)}",
            status_code=503,
            retryable=True,
        )
