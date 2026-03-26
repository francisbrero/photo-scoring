"""Local Qwen2-VL inference client."""

import logging
from pathlib import Path

from pydantic import ValidationError

from photo_score.inference.errors import LocalInferenceError
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
from photo_score.inference.local.calibration import (
    DEFAULT_CALIBRATION,
    apply_calibration,
)
from photo_score.storage.models import NormalizedAttributes

logger = logging.getLogger(__name__)


class QwenLocalClient:
    """Local inference client using Qwen2-VL-2B-Instruct."""

    def __init__(
        self,
        model_path: Path,
        device: str = "auto",
        quantize: bool = False,
    ):
        self.model_name = "local/qwen2-vl-2b-instruct"
        self.model_version = "1.0"
        self._model_path = model_path
        self._device = device
        self._quantize = quantize
        self._model = None
        self._processor = None

    def _ensure_loaded(self) -> None:
        """Lazy-load model and processor."""
        if self._model is not None:
            return

        import torch
        from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

        load_kwargs = {
            "pretrained_model_name_or_path": str(self._model_path),
            "torch_dtype": torch.float16,
        }

        if self._quantize:
            from transformers import BitsAndBytesConfig

            load_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
            )
        elif self._device == "mps":
            load_kwargs["device_map"] = "mps"
        elif self._device == "cuda":
            load_kwargs["device_map"] = "auto"

        self._model = Qwen2VLForConditionalGeneration.from_pretrained(**load_kwargs)
        self._processor = AutoProcessor.from_pretrained(str(self._model_path))

        if self._device == "mps" and not self._quantize:
            self._model = self._model.to("mps")

        logger.info(f"Loaded Qwen2-VL-2B on {self._device}")

    def _run_inference(self, image_path: Path, prompt: str) -> str:
        """Run a single inference pass on an image with a prompt."""
        import torch
        from qwen_vl_utils import process_vision_info

        self._ensure_loaded()

        # Build the conversation message
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": str(image_path)},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        text = self._processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)

        inputs = self._processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self._model.device)

        with torch.no_grad():
            generated_ids = self._model.generate(**inputs, max_new_tokens=256)

        # Only decode the newly generated tokens
        generated_ids_trimmed = [
            out_ids[len(in_ids) :]
            for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output = self._processor.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )

        return output[0] if output else ""

    def analyze_image(
        self, image_id: str, image_path: Path, model_version: str
    ) -> NormalizedAttributes:
        """Run full analysis on an image."""
        # Run aesthetic analysis
        aesthetic_text = self._run_inference(image_path, AESTHETIC_PROMPT)
        try:
            aesthetic_data = extract_json_from_response(aesthetic_text)
            aesthetic = AestheticResponse.model_validate(aesthetic_data)
        except (ValueError, ValidationError) as e:
            raise LocalInferenceError(f"Failed to parse aesthetic response: {e}")

        # Run technical analysis
        technical_text = self._run_inference(image_path, TECHNICAL_PROMPT)
        try:
            technical_data = extract_json_from_response(technical_text)
            technical = TechnicalResponse.model_validate(technical_data)
        except (ValueError, ValidationError) as e:
            raise LocalInferenceError(f"Failed to parse technical response: {e}")

        raw_attrs = NormalizedAttributes(
            image_id=image_id,
            composition=aesthetic.composition,
            subject_strength=aesthetic.subject_strength,
            visual_appeal=aesthetic.visual_appeal,
            sharpness=technical.sharpness,
            exposure_balance=technical.exposure_balance,
            noise_level=technical.noise_level,
            model_name=self.model_name,
            model_version=self.model_version,
        )

        # Apply calibration to align with cloud scores
        return apply_calibration(raw_attrs, DEFAULT_CALIBRATION)

    def analyze_metadata(self, image_path: Path) -> MetadataResponse:
        """Get description and location metadata for an image."""
        text = self._run_inference(image_path, METADATA_PROMPT)
        try:
            data = extract_json_from_response(text)
            return MetadataResponse.model_validate(data)
        except (ValueError, ValidationError) as e:
            raise LocalInferenceError(f"Failed to parse metadata response: {e}")

    def close(self) -> None:
        """Release model resources."""
        if self._model is not None:
            del self._model
            self._model = None
            del self._processor
            self._processor = None

            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

            logger.info("Released Qwen2-VL model resources")

    def __enter__(self) -> "QwenLocalClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()
