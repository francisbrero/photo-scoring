"""Error hierarchy for inference backends."""


class InferenceError(Exception):
    """Base error for all inference operations."""

    pass


class CloudInferenceError(InferenceError):
    """Error from cloud inference (OpenRouter, etc)."""

    pass


class LocalInferenceError(InferenceError):
    """Error from local inference."""

    pass


class ModelNotAvailableError(LocalInferenceError):
    """The requested local model is not downloaded."""

    pass


class HardwareInsufficientError(LocalInferenceError):
    """The local hardware cannot run the requested model."""

    pass
