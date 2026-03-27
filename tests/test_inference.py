"""Tests for inference abstractions."""

import os
from unittest.mock import patch

import pytest

from photo_score.inference.base import InferenceClient
from photo_score.inference.errors import (
    InferenceError,
    CloudInferenceError,
    LocalInferenceError,
    ModelNotAvailableError,
    HardwareInsufficientError,
)
from photo_score.inference.parsing import extract_json_from_response


class TestErrorHierarchy:
    """Tests for inference error hierarchy."""

    def test_cloud_error_is_inference_error(self):
        assert issubclass(CloudInferenceError, InferenceError)

    def test_local_error_is_inference_error(self):
        assert issubclass(LocalInferenceError, InferenceError)

    def test_model_not_available_is_local_error(self):
        assert issubclass(ModelNotAvailableError, LocalInferenceError)

    def test_hardware_insufficient_is_local_error(self):
        assert issubclass(HardwareInsufficientError, LocalInferenceError)

    def test_openrouter_error_is_cloud_error(self):
        from photo_score.inference.client import OpenRouterError

        assert issubclass(OpenRouterError, CloudInferenceError)


class TestProtocol:
    """Tests for InferenceClient protocol."""

    def test_openrouter_satisfies_protocol(self):
        """OpenRouterClient should satisfy InferenceClient protocol."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            from photo_score.inference.client import OpenRouterClient

            client = OpenRouterClient(
                api_key="test-key",
                model_name="test/model",
                model_version="1.0",
            )
            assert isinstance(client, InferenceClient)
            assert client.model_name == "test/model"
            assert client.model_version == "1.0"
            client.close()


class TestFactory:
    """Tests for create_inference_client factory."""

    def test_factory_cloud_returns_openrouter(self):
        from photo_score.inference.factory import create_inference_client

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            client = create_inference_client(
                backend="cloud",
                api_key="test-key",
                model_name="test/model",
                model_version="v1",
            )
            assert client.model_name == "test/model"
            assert client.model_version == "v1"
            client.close()

    def test_factory_local_without_extras_raises(self):
        """create_inference_client('local') should raise if extras not installed."""
        from photo_score.inference.factory import create_inference_client

        # QwenLocalClient imports torch, which won't be available in test env
        # This should raise LocalInferenceError or ImportError-derived error
        with pytest.raises((LocalInferenceError, ImportError)):
            create_inference_client(backend="local")

    def test_factory_unknown_backend_raises(self):
        from photo_score.inference.factory import create_inference_client

        with pytest.raises(ValueError, match="Unknown backend"):
            create_inference_client(backend="invalid")


class TestJsonParsing:
    """Tests for extract_json_from_response."""

    def test_plain_json(self):
        result = extract_json_from_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_markdown_code_block(self):
        result = extract_json_from_response('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_text_before_json(self):
        result = extract_json_from_response('Here is the result: {"key": "value"}')
        assert result == {"key": "value"}

    def test_text_after_json(self):
        result = extract_json_from_response('{"key": "value"} Hope this helps!')
        assert result == {"key": "value"}

    def test_nested_json(self):
        result = extract_json_from_response('{"a": {"b": 1}}')
        assert result == {"a": {"b": 1}}

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="No JSON found"):
            extract_json_from_response("no json here")

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="Invalid JSON"):
            extract_json_from_response("{broken json")


class TestCalibration:
    """Tests for local inference calibration."""

    def test_identity_calibration_is_noop(self):
        from photo_score.inference.local.calibration import (
            CalibrationMap,
            apply_calibration,
        )
        from photo_score.storage.models import NormalizedAttributes

        identity = CalibrationMap(
            composition=(1.0, 0.0),
            subject_strength=(1.0, 0.0),
            visual_appeal=(1.0, 0.0),
            sharpness=(1.0, 0.0),
            exposure_balance=(1.0, 0.0),
            noise_level=(1.0, 0.0),
        )
        attrs = NormalizedAttributes(
            image_id="test",
            composition=0.7,
            subject_strength=0.6,
            visual_appeal=0.5,
            sharpness=0.8,
            exposure_balance=0.9,
            noise_level=0.4,
            model_name="test",
            model_version="1.0",
        )

        result = apply_calibration(attrs, identity)
        assert result.composition == pytest.approx(0.7)
        assert result.sharpness == pytest.approx(0.8)

    def test_calibration_clamps_to_unit(self):
        from photo_score.inference.local.calibration import (
            CalibrationMap,
            apply_calibration,
        )
        from photo_score.storage.models import NormalizedAttributes

        aggressive = CalibrationMap(
            composition=(2.0, 0.5),  # Would produce >1.0
            subject_strength=(1.0, -0.5),  # Would produce <0.0 for low values
            visual_appeal=(1.0, 0.0),
            sharpness=(1.0, 0.0),
            exposure_balance=(1.0, 0.0),
            noise_level=(1.0, 0.0),
        )
        attrs = NormalizedAttributes(
            image_id="test",
            composition=0.9,  # 2.0*0.9 + 0.5 = 2.3 -> clamped to 1.0
            subject_strength=0.1,  # 1.0*0.1 - 0.5 = -0.4 -> clamped to 0.0
            visual_appeal=0.5,
            sharpness=0.5,
            exposure_balance=0.5,
            noise_level=0.5,
            model_name="test",
            model_version="1.0",
        )

        result = apply_calibration(attrs, aggressive)
        assert result.composition == 1.0
        assert result.subject_strength == 0.0

    def test_default_calibration_scales_down(self):
        from photo_score.inference.local.calibration import (
            DEFAULT_CALIBRATION,
            apply_calibration,
        )
        from photo_score.storage.models import NormalizedAttributes

        attrs = NormalizedAttributes(
            image_id="test",
            composition=0.8,
            subject_strength=0.8,
            visual_appeal=0.8,
            sharpness=0.8,
            exposure_balance=0.8,
            noise_level=0.8,
            model_name="test",
            model_version="1.0",
        )

        result = apply_calibration(attrs, DEFAULT_CALIBRATION)
        # All slopes < 1.0, so all calibrated values should be lower
        assert result.composition < 0.8
        assert result.subject_strength < 0.8
        assert result.visual_appeal < 0.8
        assert result.sharpness < 0.8


class TestConfigBackend:
    """Tests for config schema backend field."""

    def test_default_backend_is_cloud(self):
        from photo_score.config.schema import ModelConfig

        config = ModelConfig()
        assert config.backend == "cloud"

    def test_backend_can_be_set(self):
        from photo_score.config.schema import ModelConfig

        config = ModelConfig(backend="local")
        assert config.backend == "local"
