"""OpenRouter service for AI inference on images."""

import asyncio
import base64
import hashlib
import tempfile
from pathlib import Path

from ..config import get_settings


class InferenceError(Exception):
    """Raised when inference fails."""

    def __init__(self, message: str, retryable: bool = False):
        self.message = message
        self.retryable = retryable
        super().__init__(message)


class OpenRouterService:
    """Service for running AI inference on images via OpenRouter."""

    def __init__(self):
        self.settings = get_settings()
        self._client = None

    def _get_client(self):
        """Lazy-load the OpenRouter client."""
        if self._client is None:
            # Import here to avoid loading at module level
            from photo_score.inference.client import OpenRouterClient

            self._client = OpenRouterClient(api_key=self.settings.openrouter_api_key)
        return self._client

    async def analyze_image(self, image_data: bytes, image_hash: str) -> dict:
        """Analyze an image and return normalized attributes.

        Args:
            image_data: Raw image bytes
            image_hash: SHA256 hash of the image for identification

        Returns:
            Dictionary with normalized attributes:
            - composition, subject_strength, visual_appeal (aesthetic)
            - sharpness, exposure_balance, noise_level (technical)
            - model_name, model_version

        Raises:
            InferenceError: If inference fails
        """
        # Write image to temp file (OpenRouterClient expects file path)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(image_data)
            temp_path = Path(f.name)

        try:
            # Run inference in thread pool (client is synchronous)
            client = self._get_client()
            attributes = await asyncio.to_thread(
                client.analyze_image,
                image_id=image_hash,
                image_path=temp_path,
                model_version="cloud-v1",
            )

            # Convert to dict for JSON serialization
            return {
                "image_id": attributes.image_id,
                "composition": attributes.composition,
                "subject_strength": attributes.subject_strength,
                "visual_appeal": attributes.visual_appeal,
                "sharpness": attributes.sharpness,
                "exposure_balance": attributes.exposure_balance,
                "noise_level": attributes.noise_level,
                "model_name": attributes.model_name,
                "model_version": attributes.model_version,
            }

        except Exception as e:
            # Map OpenRouter errors to InferenceError
            error_msg = str(e)
            retryable = "rate limit" in error_msg.lower() or "timeout" in error_msg.lower()
            raise InferenceError(f"Inference failed: {error_msg}", retryable=retryable) from e

        finally:
            # Clean up temp file
            try:
                temp_path.unlink()
            except Exception:
                pass

    async def analyze_image_metadata(self, image_data: bytes, image_hash: str) -> dict:
        """Analyze an image and return metadata (description, location).

        Args:
            image_data: Raw image bytes
            image_hash: SHA256 hash of the image

        Returns:
            Dictionary with:
            - description: str
            - location_name: str | None
            - location_country: str | None

        Raises:
            InferenceError: If inference fails
        """
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(image_data)
            temp_path = Path(f.name)

        try:
            client = self._get_client()
            metadata = await asyncio.to_thread(
                client.analyze_metadata,
                image_path=temp_path,
            )

            return {
                "description": metadata.description,
                "location_name": metadata.location_name,
                "location_country": metadata.location_country,
            }

        except Exception as e:
            error_msg = str(e)
            retryable = "rate limit" in error_msg.lower() or "timeout" in error_msg.lower()
            raise InferenceError(
                f"Metadata inference failed: {error_msg}", retryable=retryable
            ) from e

        finally:
            try:
                temp_path.unlink()
            except Exception:
                pass

    @staticmethod
    def compute_scores(attributes: dict) -> dict:
        """Compute aesthetic, technical, and final scores from attributes.

        Uses the same weights as the photo_score library.

        Args:
            attributes: Dict with the 6 normalized attributes

        Returns:
            Dictionary with:
            - aesthetic_score: float (0-1)
            - technical_score: float (0-1)
            - final_score: float (0-100)
        """
        # Aesthetic score (0-1)
        aesthetic_score = (
            attributes["composition"] * 0.4
            + attributes["subject_strength"] * 0.35
            + attributes["visual_appeal"] * 0.25
        )

        # Technical score (0-1)
        technical_score = (
            attributes["sharpness"] * 0.4
            + attributes["exposure_balance"] * 0.35
            + attributes["noise_level"] * 0.25
        )

        # Final score (0-100)
        final_score = (aesthetic_score * 0.6 + technical_score * 0.4) * 100

        # Apply threshold penalties
        if attributes["sharpness"] < 0.2:
            penalty = (0.2 - attributes["sharpness"]) / 0.2 * 0.5
            final_score *= 1 - penalty

        if attributes["exposure_balance"] < 0.1:
            penalty = (0.1 - attributes["exposure_balance"]) / 0.1 * 0.3
            final_score *= 1 - penalty

        return {
            "aesthetic_score": round(aesthetic_score, 4),
            "technical_score": round(technical_score, 4),
            "final_score": round(final_score, 2),
        }

    @staticmethod
    def compute_image_hash(image_data: bytes) -> str:
        """Compute SHA256 hash of image data."""
        return hashlib.sha256(image_data).hexdigest()

    @staticmethod
    def decode_base64_image(base64_data: str) -> bytes:
        """Decode base64-encoded image data.

        Handles both raw base64 and data URL format.
        """
        # Handle data URL format (e.g., "data:image/jpeg;base64,...")
        if base64_data.startswith("data:"):
            base64_data = base64_data.split(",", 1)[1]

        return base64.b64decode(base64_data)
