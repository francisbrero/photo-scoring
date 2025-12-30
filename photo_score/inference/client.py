"""OpenRouter API client for vision model inference."""

import base64
import json
import logging
import os
import re
import time
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image, ImageOps
from pydantic import ValidationError

# Register HEIC/HEIF support
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass  # pillow-heif not installed, HEIC files won't work

from photo_score.inference.prompts import AESTHETIC_PROMPT, TECHNICAL_PROMPT, METADATA_PROMPT
from photo_score.inference.schemas import AestheticResponse, TechnicalResponse, MetadataResponse
from photo_score.storage.models import NormalizedAttributes

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_IMAGE_DIMENSION = 2048

# Model tiers for different tasks
# Scoring requires nuanced judgment - use higher quality model
MODEL_SCORING = "anthropic/claude-3.5-sonnet"  # $3/M input, $15/M output
# Metadata is simpler (description + location) - use cheaper model
MODEL_METADATA = "anthropic/claude-3-haiku"    # $0.25/M input, $1.25/M output (12x cheaper)


class OpenRouterError(Exception):
    """Error from OpenRouter API."""

    pass


class OpenRouterClient:
    """Client for OpenRouter vision model API."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "anthropic/claude-3.5-sonnet",
    ):
        """Initialize client.

        Args:
            api_key: OpenRouter API key. Defaults to OPENROUTER_API_KEY env var.
            model_name: Model identifier for OpenRouter.
        """
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key required. Set OPENROUTER_API_KEY environment variable."
            )

        self.model_name = model_name
        self.client = httpx.Client(timeout=120.0)

    def _load_and_encode_image(self, image_path: Path) -> tuple[str, str]:
        """Load image, resize if needed, and encode to base64.

        Returns:
            Tuple of (base64_data, media_type)
        """
        with Image.open(image_path) as img:
            # Apply EXIF orientation (fixes rotated images from phones)
            img = ImageOps.exif_transpose(img)

            # Convert to RGB if needed (handles RGBA, P mode, etc.)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            # Resize if too large
            if max(img.size) > MAX_IMAGE_DIMENSION:
                ratio = MAX_IMAGE_DIMENSION / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Encode to JPEG
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

            return base64_data, "image/jpeg"

    def _call_api(
        self,
        image_path: Path,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 256,
    ) -> dict:
        """Make API call with image and prompt.

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
            except (httpx.TimeoutException, httpx.RemoteProtocolError, httpx.ConnectError) as e:
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

        # Extract JSON from response (handle markdown code blocks and nested structures)
        # First try to extract from markdown code block
        code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON by matching balanced braces
        # Find the first { and extract everything to the matching }
        start_idx = content.find("{")
        if start_idx == -1:
            raise OpenRouterError(f"No JSON found in response: {content}")

        # Count braces to find matching closing brace
        depth = 0
        end_idx = start_idx
        for i, char in enumerate(content[start_idx:], start_idx):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end_idx = i + 1
                    break

        json_str = content[start_idx:end_idx]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise OpenRouterError(f"Invalid JSON in response: {e}\nContent: {content}")

    def analyze_aesthetic(self, image_path: Path) -> AestheticResponse:
        """Analyze aesthetic qualities of an image."""
        result = self._call_api(image_path, AESTHETIC_PROMPT)
        try:
            return AestheticResponse.model_validate(result)
        except ValidationError as e:
            raise OpenRouterError(f"Invalid aesthetic response: {e}")

    def analyze_technical(self, image_path: Path) -> TechnicalResponse:
        """Analyze technical qualities of an image."""
        result = self._call_api(image_path, TECHNICAL_PROMPT)
        try:
            return TechnicalResponse.model_validate(result)
        except ValidationError as e:
            raise OpenRouterError(f"Invalid technical response: {e}")

    def analyze_metadata(self, image_path: Path) -> MetadataResponse:
        """Get description and location metadata for an image.

        Uses a cheaper model (Claude 3 Haiku) since this task is simpler
        than nuanced photo scoring.
        """
        result = self._call_api(image_path, METADATA_PROMPT, model=MODEL_METADATA)
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
