"""OpenRouter service for AI inference on images.

Self-contained implementation that doesn't depend on the photo_score package.
"""

import asyncio
import base64
import hashlib
import json
import logging
import re
from io import BytesIO

import httpx
from PIL import Image, ImageOps

# Register HEIC/HEIF support
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    pass  # pillow-heif not installed

from ..config import get_settings

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_IMAGE_DIMENSION = 2048

# Model for scoring (requires nuanced judgment)
MODEL_SCORING = "anthropic/claude-3.5-sonnet"
# Model for metadata (simpler task, cheaper)
MODEL_METADATA = "anthropic/claude-3-haiku"

# Prompts
AESTHETIC_PROMPT = """You are a harsh photography critic evaluating images for a curated portfolio. Most travel and casual photos score between 0.3 and 0.6. Scores above 0.7 are rare and require exceptional qualities.

Evaluate this photograph's aesthetic qualities on a scale from 0.0 to 1.0.

CALIBRATION GUIDE:
- 0.9-1.0: Portfolio/publishable work. Exceptional light, decisive moment, gallery-worthy.
- 0.7-0.8: Strong, intentional, near-publishable. Clear vision, would survive multiple editing passes.
- 0.5-0.6: Competent but unremarkable. Technically fine, visually inert. Generic travel photo.
- 0.3-0.4: Flawed, tourist-level. Lazy composition, no story, "camera did its job" not "photographer made decisions."
- 0.0-0.2: Compositionally broken. No redeeming aesthetic value.

Respond with ONLY a JSON object:
{
  "composition": <float 0.0-1.0>,
  "subject_strength": <float 0.0-1.0>,
  "visual_appeal": <float 0.0-1.0>
}

Attribute definitions:
- composition: Intentional framing, subject hierarchy, use of space. Penalize center-weighted laziness, excess dead space, cluttered frames. Ask: "Did the photographer make deliberate decisions?"
- subject_strength: Is there a clear subject? Does the eye know where to go? Penalize competing elements, blocked subjects, unclear focal points. A person in frame doesn't automatically mean strong subject.
- visual_appeal: Emotional impact, tension, story, surprise. Penalize "pleasant but inert" images the eye scans once and leaves. Stock photo aesthetics score low. Ask: "Would this survive a second cull?"

Be harsh. Most photos are mediocre. Score accordingly."""

TECHNICAL_PROMPT = """You are evaluating the technical execution of a photograph. Technical competence is necessary but not sufficient for a good photo. "Camera did its job" is a 0.5-0.6, not higher.

IMPORTANT: Technical execution includes how well the photographer controlled ALL elements in the frame, not just camera settings. Distracting foreground elements, poor subject placement, objects blocking the scene, or jarring colors that weren't managed are TECHNICAL FAILURES, not just aesthetic ones.

Evaluate on a scale from 0.0 to 1.0.

CALIBRATION GUIDE:
- 0.9-1.0: Exceptional technical mastery. Perfect focus, exposure serves the vision, no distractions, complete control of the frame.
- 0.7-0.8: Strong technical execution. Correct exposure, good sharpness, disciplined, minimal distractions.
- 0.5-0.6: Acceptable, no obvious mistakes. Auto-mode competence. May have minor distracting elements. "Fine."
- 0.3-0.4: Technical issues present. Soft focus, exposure problems, distracting elements that harm the image, poor subject placement.
- 0.0-0.2: Technically broken. Unusable blur, severe exposure failure, or elements that completely undermine the image.

Respond with ONLY a JSON object:
{
  "sharpness": <float 0.0-1.0>,
  "exposure_balance": <float 0.0-1.0>,
  "noise_level": <float 0.0-1.0>
}

Attribute definitions:
- sharpness: Focus quality where it matters AND absence of distracting elements. Is the intended subject sharp and unobstructed? A sharp photo with a distracting foreground object blocking the scene scores lower. Motion blur, missed focus, soft images, or obstructed subjects all reduce score. "Acceptable" is 0.5-0.6.
- exposure_balance: Does exposure serve the image? Consider whether bright/saturated foreground elements (like safety gear, bright clothing) create exposure or color distractions that weren't managed. Blown highlights, crushed shadows, flat lighting, or jarring color imbalances reduce score. Correct auto-exposure with no distractions is 0.5-0.6.
- noise_level: Clean image vs visible noise/grain. Modern cameras at low ISO should score 0.7+. High ISO noise, banding, or artifacts reduce score.

Be calibrated. Most casual photos are technically "fine" (0.5-0.6), not "excellent". Photos with distracting elements the photographer failed to manage score lower."""

METADATA_PROMPT = """Analyze this photograph and provide:
1. A brief description (1-3 sentences) of what's in the photo - the subject, scene, and any notable elements
2. The location where this photo was likely taken, if identifiable

Respond with ONLY a JSON object:
{
  "description": "<1-3 sentence description of the photo>",
  "location_name": "<city, region, or landmark name in English, or null if unknown>",
  "location_country": "<country name in English, or null if unknown>"
}

Be concise and factual. Focus on what's visible in the image. If the location cannot be determined from visible landmarks, signs, or distinctive features, use null for location fields."""

# Feature extraction prompt (used for rich critique context)
FEATURE_EXTRACTION_PROMPT = """Analyze this photograph and extract detailed features. Be objective and thorough.

Respond with ONLY a JSON object:
{
  "scene_type": "<landscape|portrait|street|architecture|nature|food|event|other>",
  "main_subject": "<brief description of the main subject>",
  "subject_position": "<center|rule_of_thirds|off_center|multiple>",
  "background": "<clean|busy|blurred|contextual>",
  "lighting": "<natural_soft|natural_harsh|golden_hour|blue_hour|artificial|mixed|low_light>",
  "color_palette": "<vibrant|muted|monochrome|warm|cool|neutral>",
  "depth_of_field": "<shallow|medium|deep>",
  "motion": "<static|implied|blur|frozen>",
  "human_presence": "<none|main_subject|secondary|crowd>",
  "text_or_signs": <true|false>,
  "weather_visible": "<clear|cloudy|rain|fog|none>",
  "time_of_day": "<dawn|morning|midday|afternoon|golden_hour|dusk|night|unknown>",
  "technical_issues": ["<list any: blur, noise, overexposed, underexposed, tilted, none>"],
  "notable_elements": ["<list 2-3 notable visual elements>"],
  "estimated_location_type": "<urban|rural|coastal|mountain|indoor|tourist_site|unknown>"
}

Be factual. Report what you observe, not interpretations."""

# Critique prompt template (filled with context before use)
CRITIQUE_PROMPT_TEMPLATE = """You are a photography instructor reviewing this image to help the photographer improve deliberately.

IMAGE CONTEXT:
- Scene type: {scene_type}
- Main subject: {main_subject}
- Subject position: {subject_position}
- Background: {background}
- Lighting: {lighting}
- Color palette: {color_palette}
- Depth of field: {depth_of_field}
- Time of day: {time_of_day}

SCORES (0-1 scale):
- Composition: {composition:.2f}
- Subject strength: {subject_strength:.2f}
- Visual appeal: {visual_appeal:.2f}
- Sharpness: {sharpness:.2f}
- Exposure: {exposure_balance:.2f}
- Noise level: {noise_level:.2f} (1.0 = clean)
- Final score: {final_score:.0f}/100

Write a structured critique as a photography instructor. Be educational, specific, and constructive.

Respond with ONLY a JSON object:
{{
  "summary": "<2-3 sentences: overall assessment of the image's strengths and main limitations>",
  "working_well": [
    "<specific strength 1 with explanation of WHY it works>",
    "<specific strength 2 with explanation>"
  ],
  "could_improve": [
    "<specific issue 1 with concrete suggestion for improvement>",
    "<specific issue 2 with actionable advice>"
  ],
  "key_recommendation": "<single most impactful thing the photographer could do differently, either in capture or post-processing>"
}}

GUIDELINES:
- Ground observations in what you SEE in the image, not generic advice
- Explain WHY something works or doesn't work in this specific context
- For improvements, give concrete suggestions (e.g., "lower the camera angle", "crop from the top", "return at golden hour")
- Acknowledge what's working before critiquing weaknesses
- Be educational, not snarky or dismissive
- Consider scene type when evaluating (centered subjects work for some scenes)
- For landscapes: consider light quality, depth layering, foreground interest
- For portraits: consider expression, background separation, eye contact
- For architecture: consider lines, symmetry, perspective"""


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

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(timeout=120.0)
        return self._client

    def _load_and_encode_image(self, image_data: bytes) -> tuple[str, str]:
        """Load image from bytes, resize if needed, and encode to base64.

        Returns:
            Tuple of (base64_data, media_type)
        """
        if not image_data:
            raise InferenceError("Empty image data")

        logger.info(f"Loading image: {len(image_data)} bytes, first 20 bytes: {image_data[:20]}")

        try:
            img = Image.open(BytesIO(image_data))
        except Exception as e:
            raise InferenceError(
                f"Cannot open image: {e}. Data length: {len(image_data)}, type: {type(image_data)}"
            )

        with img:
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
        image_data: bytes,
        prompt: str,
        model: str,
        max_tokens: int = 256,
    ) -> dict:
        """Make API call with image and prompt.

        Args:
            image_data: Raw image bytes.
            prompt: Text prompt for analysis.
            model: Model to use.
            max_tokens: Maximum tokens in response.

        Returns:
            Parsed JSON response from model.
        """
        base64_data, media_type = self._load_and_encode_image(image_data)
        client = self._get_client()

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{media_type};base64,{base64_data}"},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0,
        }

        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }

        # Retry logic for rate limits and timeouts
        max_retries = 5
        last_error = None
        import time

        for attempt in range(max_retries):
            try:
                response = client.post(OPENROUTER_API_URL, json=payload, headers=headers)
            except (
                httpx.TimeoutException,
                httpx.RemoteProtocolError,
                httpx.ConnectError,
            ) as e:
                wait_time = 2 ** (attempt + 1)
                logger.warning(f"Network error on attempt {attempt + 1}, waiting {wait_time}s: {e}")
                last_error = e
                time.sleep(wait_time)
                continue

            if response.status_code == 429:
                wait_time = 2 ** (attempt + 1)
                logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                time.sleep(wait_time)
                continue

            if response.status_code != 200:
                raise InferenceError(f"API error {response.status_code}: {response.text}")

            break
        else:
            raise InferenceError(f"Max retries exceeded: {last_error}", retryable=True)

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        # Extract JSON from response
        return self._parse_json_response(content)

    def _parse_json_response(self, content: str) -> dict:
        """Parse JSON from model response, handling markdown code blocks."""
        # First try to extract from markdown code block
        code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON by matching balanced braces
        start_idx = content.find("{")
        if start_idx == -1:
            logger.error(
                f"No JSON found in model response. Content length: {len(content)}. Content: {content[:500]}"
            )
            raise InferenceError(f"No JSON found in response: {content[:200]}")

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
            raise InferenceError(f"Invalid JSON in response: {e}\nContent: {content}")

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
        try:
            # Run aesthetic analysis
            aesthetic = await asyncio.to_thread(
                self._call_api, image_data, AESTHETIC_PROMPT, MODEL_SCORING
            )

            # Run technical analysis
            technical = await asyncio.to_thread(
                self._call_api, image_data, TECHNICAL_PROMPT, MODEL_SCORING
            )

            return {
                "image_id": image_hash,
                "composition": aesthetic.get("composition", 0.5),
                "subject_strength": aesthetic.get("subject_strength", 0.5),
                "visual_appeal": aesthetic.get("visual_appeal", 0.5),
                "sharpness": technical.get("sharpness", 0.5),
                "exposure_balance": technical.get("exposure_balance", 0.5),
                "noise_level": technical.get("noise_level", 0.5),
                "model_name": MODEL_SCORING,
                "model_version": "cloud-v1",
            }

        except Exception as e:
            error_msg = str(e)
            retryable = "rate limit" in error_msg.lower() or "timeout" in error_msg.lower()
            raise InferenceError(f"Inference failed: {error_msg}", retryable=retryable) from e

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
        try:
            metadata = await asyncio.to_thread(
                self._call_api, image_data, METADATA_PROMPT, MODEL_METADATA
            )

            return {
                "description": metadata.get("description", ""),
                "location_name": metadata.get("location_name"),
                "location_country": metadata.get("location_country"),
            }

        except Exception as e:
            error_msg = str(e)
            retryable = "rate limit" in error_msg.lower() or "timeout" in error_msg.lower()
            raise InferenceError(
                f"Metadata inference failed: {error_msg}", retryable=retryable
            ) from e

    async def extract_features(self, image_data: bytes) -> dict:
        """Extract scene features from an image for rich critique context.

        Uses a cheap model (Haiku) for cost efficiency.

        Args:
            image_data: Raw image bytes

        Returns:
            Dictionary with scene features:
            - scene_type, main_subject, subject_position, background
            - lighting, color_palette, depth_of_field, time_of_day
            - human_presence, weather_visible, notable_elements, etc.

        Raises:
            InferenceError: If extraction fails
        """
        try:
            features = await asyncio.to_thread(
                self._call_api, image_data, FEATURE_EXTRACTION_PROMPT, MODEL_METADATA
            )

            # Ensure required fields have defaults
            return {
                "scene_type": features.get("scene_type", "other"),
                "main_subject": features.get("main_subject", "unclear"),
                "subject_position": features.get("subject_position", "center"),
                "background": features.get("background", "unknown"),
                "lighting": features.get("lighting", "unknown"),
                "color_palette": features.get("color_palette", "neutral"),
                "depth_of_field": features.get("depth_of_field", "medium"),
                "motion": features.get("motion", "static"),
                "human_presence": features.get("human_presence", "none"),
                "text_or_signs": features.get("text_or_signs", False),
                "weather_visible": features.get("weather_visible", "none"),
                "time_of_day": features.get("time_of_day", "unknown"),
                "technical_issues": features.get("technical_issues", []),
                "notable_elements": features.get("notable_elements", []),
                "estimated_location_type": features.get("estimated_location_type", "unknown"),
            }

        except Exception as e:
            error_msg = str(e)
            retryable = "rate limit" in error_msg.lower() or "timeout" in error_msg.lower()
            raise InferenceError(
                f"Feature extraction failed: {error_msg}", retryable=retryable
            ) from e

    async def generate_critique(
        self,
        image_data: bytes,
        features: dict,
        attributes: dict,
        final_score: float,
    ) -> dict:
        """Generate a rich, contextual critique using features and scores.

        Args:
            image_data: Raw image bytes
            features: Scene features from extract_features()
            attributes: Normalized attributes from analyze_image()
            final_score: Final computed score (0-100)

        Returns:
            Dictionary with:
            - summary: str (2-3 sentence overall assessment)
            - working_well: list[str] (specific strengths)
            - could_improve: list[str] (specific suggestions)
            - key_recommendation: str (single most impactful advice)

        Raises:
            InferenceError: If critique generation fails
        """
        # Build the prompt with context
        prompt = CRITIQUE_PROMPT_TEMPLATE.format(
            scene_type=features.get("scene_type", "unknown"),
            main_subject=features.get("main_subject", "unclear"),
            subject_position=features.get("subject_position", "unknown"),
            background=features.get("background", "unknown"),
            lighting=features.get("lighting", "unknown"),
            color_palette=features.get("color_palette", "unknown"),
            depth_of_field=features.get("depth_of_field", "unknown"),
            time_of_day=features.get("time_of_day", "unknown"),
            composition=attributes.get("composition", 0.5),
            subject_strength=attributes.get("subject_strength", 0.5),
            visual_appeal=attributes.get("visual_appeal", 0.5),
            sharpness=attributes.get("sharpness", 0.5),
            exposure_balance=attributes.get("exposure_balance", 0.5),
            noise_level=attributes.get("noise_level", 0.5),
            final_score=final_score,
        )

        try:
            critique = await asyncio.to_thread(
                self._call_api, image_data, prompt, MODEL_SCORING, max_tokens=1024
            )

            return {
                "summary": critique.get("summary", ""),
                "working_well": critique.get("working_well", []),
                "could_improve": critique.get("could_improve", []),
                "key_recommendation": critique.get("key_recommendation", ""),
            }

        except Exception as e:
            error_msg = str(e)
            retryable = "rate limit" in error_msg.lower() or "timeout" in error_msg.lower()
            raise InferenceError(
                f"Critique generation failed: {error_msg}", retryable=retryable
            ) from e

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
    def format_explanation(critique: dict) -> str:
        """Format the critique into a readable explanation string.

        Args:
            critique: Dict from generate_critique() with summary, working_well,
                     could_improve, and key_recommendation

        Returns:
            Formatted explanation string with structured sections
        """
        parts = []

        if critique.get("summary"):
            parts.append(critique["summary"])

        if critique.get("working_well"):
            strengths = critique["working_well"][:2]  # Top 2 strengths
            parts.append("**What's working:** " + " ".join(strengths))

        if critique.get("could_improve"):
            improvements = critique["could_improve"][:2]  # Top 2 improvements
            parts.append("**Could improve:** " + " ".join(improvements))

        return "\n\n".join(parts) if parts else "Unable to generate critique."

    @staticmethod
    def format_improvements(critique: dict) -> str:
        """Extract and format improvements from the critique.

        Args:
            critique: Dict from generate_critique()

        Returns:
            Formatted improvement suggestions with key recommendation
        """
        improvements = []

        # Add specific improvement suggestions
        if critique.get("could_improve"):
            improvements.extend(critique["could_improve"][:2])

        # Add key recommendation
        if critique.get("key_recommendation"):
            improvements.append(f"**Key recommendation:** {critique['key_recommendation']}")

        if not improvements:
            return "No specific improvements identified."

        return " | ".join(improvements)

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
