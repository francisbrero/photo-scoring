"""Factory for creating inference clients."""

from photo_score.inference.base import InferenceClient
from photo_score.inference.errors import (
    CloudInferenceError,
    HardwareInsufficientError,
    LocalInferenceError,
    ModelNotAvailableError,
)


def create_inference_client(
    backend: str = "cloud",
    model_name: str = "anthropic/claude-3.5-sonnet",
    model_version: str = "unknown",
    api_key: str | None = None,
) -> InferenceClient:
    """Create an inference client for the specified backend.

    Args:
        backend: "cloud", "local", or "auto".
        model_name: Model identifier (used for cloud backend).
        model_version: Version string.
        api_key: API key (used for cloud backend).

    Returns:
        An InferenceClient instance.
    """
    if backend == "cloud":
        from photo_score.inference.client import OpenRouterClient

        return OpenRouterClient(
            api_key=api_key,
            model_name=model_name,
            model_version=model_version,
        )
    elif backend == "local":
        return _create_local_client()
    elif backend == "auto":
        return _create_auto_client(
            model_name=model_name,
            model_version=model_version,
            api_key=api_key,
        )
    else:
        raise ValueError(
            f"Unknown backend: {backend!r}. Use 'cloud', 'local', or 'auto'."
        )


def _create_local_client() -> InferenceClient:
    """Create a local inference client, checking all prerequisites."""
    try:
        from photo_score.inference.local.qwen_client import QwenLocalClient
    except ImportError:
        raise LocalInferenceError(
            "Local inference extras not installed.\n"
            "Install with: uv pip install 'photo-score[local]'"
        )

    from photo_score.inference.local.hardware import detect_capabilities
    from photo_score.inference.local.model_manager import ModelManager

    caps = detect_capabilities()
    if not caps.can_run_local:
        raise HardwareInsufficientError(
            f"Insufficient hardware for local inference.\n"
            f"Detected: device={caps.device}, "
            f"CUDA VRAM={caps.cuda_vram_gb or 'N/A'}GB\n"
            f"Requires: Apple Silicon (MPS) or CUDA GPU with >=4GB VRAM."
        )

    manager = ModelManager()
    if not manager.is_model_available():
        raise ModelNotAvailableError(
            "Local model not downloaded.\nRun: photo-score models download"
        )

    model_path = manager.get_model_path()
    return QwenLocalClient(
        model_path=model_path,
        device=caps.device,
        quantize=(caps.device == "cuda"),
    )


def _create_auto_client(
    model_name: str,
    model_version: str,
    api_key: str | None,
) -> InferenceClient:
    """Try local first, fall back to cloud."""
    try:
        return _create_local_client()
    except (LocalInferenceError, ImportError):
        pass

    # Fall back to cloud
    try:
        from photo_score.inference.client import OpenRouterClient

        return OpenRouterClient(
            api_key=api_key,
            model_name=model_name,
            model_version=model_version,
        )
    except CloudInferenceError:
        raise CloudInferenceError(
            "No inference backend available.\n"
            "Either install local extras (`uv pip install 'photo-score[local]'`) "
            "or set OPENROUTER_API_KEY for cloud inference."
        )
