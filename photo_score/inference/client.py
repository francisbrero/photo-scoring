"""OpenRouter API client for vision model inference."""

import logging
import os
import time
from pathlib import Path

import httpx
from pydantic import ValidationError

from photo_score.inference.errors import CloudInferenceError
from photo_score.inference.image_utils import (
    load_and_preprocess_image,
    encode_image_base64,
)
from photo_score.inference.parsing import extract_json_from_response
from photo_score.inference.prompts import (
    AESTHETIC_PROMPT,
    TECHNICAL_PROMPT,
    METADATA_PROMPT,
)
from photo_score.inference.schemas import (
    AestheticResponse,
    TechnicalResponse,
    MetadataResponse,
)
from photo_score.storage.models import NormalizedAttributes

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model tiers for different tasks
# Scoring requires nuanced judgment - use higher quality model
MODEL_SCORING = "anthropic/claude-3.5-sonnet"  # $3/M input, $15/M output
# Metadata is simpler (description + location) - use cheaper model
MODEL_METADATA = (
    "anthropic/claude-3-haiku"  # $0.25/M input, $1.25/M output (12x cheaper)
)


class OpenRouterError(CloudInferenceError):
    """Error from OpenRouter API."""

    pass


class OpenRouterClient:
    """Client for OpenRouter vision model API."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "anthropic/claude-3.5-sonnet",
        model_version: str = "unknown",
    ):
        """Initialize client.

        Args:
            api_key: OpenRouter API key. Defaults to OPENROUTER_API_KEY env var.
            model_name: Model identifier for OpenRouter.
            model_version: Version string for this model configuration.
        """
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise CloudInferenceError(
                "OpenRouter API key required. Set OPENROUTER_API_KEY environment variable."
            )

        self.model_name = model_name
        self.model_version = model_version
        self.client = httpx.Client(timeout=120.0)

    def _load_and_encode_image(self, image_path: Path) -> tuple[str, str]:
        """Load image, resize if needed, and encode to base64.

        Returns:
            Tuple of (base64_data, media_type)
        """
        img = load_and_preprocess_image(image_path)
        return encode_image_base64(img)

    def call_api(
        self,
        image_path: Path,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 256,
    ) -> dict:
        """Make API call with image and prompt.

        This is the primary method for making vision model API calls.
        Used by both internal methods and external modules (composite scorer, benchmark).

        Args:
            image_path: Path to image file.
            prompt: Text prompt for analysis.
            model: Model to use (defaults to self.model_name).
            max_tokens: Maximum tokens in response (default 256).

        Returns:
            Parsed JSON response from model.
        """
        base64_data, media_type = self._load_and_encode_image(image_path)
        use_model = model or self.model_name

        payload = {
            "model": use_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{base64_data}"
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Retry logic for rate limits, timeouts, and connection errors
        max_retries = 5
        last_error = None
        for attempt in range(max_retries):
            try:
                response = self.client.post(
                    OPENROUTER_API_URL, json=payload, headers=headers
                )
            except (
                httpx.TimeoutException,
                httpx.RemoteProtocolError,
                httpx.ConnectError,
            ) as e:
                wait_time = 2 ** (attempt + 1)
                logger.warning(
                    f"Network error on attempt {attempt + 1}, waiting {wait_time}s before retry: {e}"
                )
                last_error = e
                time.sleep(wait_time)
                continue

            if response.status_code == 429:
                wait_time = 2 ** (attempt + 1)
                logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                time.sleep(wait_time)
                continue

            if response.status_code != 200:
                raise OpenRouterError(
                    f"API error {response.status_code}: {response.text}"
                )

            break
        else:
            raise OpenRouterError(f"Max retries exceeded: {last_error}")

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        try:
            return extract_json_from_response(content)
        except ValueError as e:
            raise OpenRouterError(str(e))

    def analyze_aesthetic(self, image_path: Path) -> AestheticResponse:
        """Analyze aesthetic qualities of an image."""
        result = self.call_api(image_path, AESTHETIC_PROMPT)
        try:
            return AestheticResponse.model_validate(result)
        except ValidationError as e:
            raise OpenRouterError(f"Invalid aesthetic response: {e}")

    def analyze_technical(self, image_path: Path) -> TechnicalResponse:
        """Analyze technical qualities of an image."""
        result = self.call_api(image_path, TECHNICAL_PROMPT)
        try:
            return TechnicalResponse.model_validate(result)
        except ValidationError as e:
            raise OpenRouterError(f"Invalid technical response: {e}")

    def analyze_metadata(self, image_path: Path) -> MetadataResponse:
        """Get description and location metadata for an image.

        Uses a cheaper model (Claude 3 Haiku) since this task is simpler
        than nuanced photo scoring.
        """
        result = self.call_api(image_path, METADATA_PROMPT, model=MODEL_METADATA)
        try:
            return MetadataResponse.model_validate(result)
        except ValidationError as e:
            raise OpenRouterError(f"Invalid metadata response: {e}")

    def analyze_image(
        self, image_id: str, image_path: Path, model_version: str
    ) -> NormalizedAttributes:
        """Run full analysis on an image.

        Args:
            image_id: Unique identifier for the image.
            image_path: Path to the image file.
            model_version: Version string for the model.

        Returns:
            NormalizedAttributes with all scores.
        """
        aesthetic = self.analyze_aesthetic(image_path)
        technical = self.analyze_technical(image_path)

        return NormalizedAttributes(
            image_id=image_id,
            composition=aesthetic.composition,
            subject_strength=aesthetic.subject_strength,
            visual_appeal=aesthetic.visual_appeal,
            sharpness=technical.sharpness,
            exposure_balance=technical.exposure_balance,
            noise_level=technical.noise_level,
            model_name=self.model_name,
            model_version=model_version,
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self) -> "OpenRouterClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()
