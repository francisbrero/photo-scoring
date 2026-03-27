"""Vision model inference via OpenRouter and local models.

Main exports:
- OpenRouterClient: HTTP client for vision model API calls
- OpenRouterError: Exception for API errors
- InferenceClient: Protocol for inference backends
- InferenceError: Base exception for all inference errors
- create_inference_client: Factory function
"""

from photo_score.inference.base import InferenceClient
from photo_score.inference.client import OpenRouterClient, OpenRouterError
from photo_score.inference.errors import (
    CloudInferenceError,
    InferenceError,
    LocalInferenceError,
)
from photo_score.inference.factory import create_inference_client

__all__ = [
    "OpenRouterClient",
    "OpenRouterError",
    "InferenceClient",
    "InferenceError",
    "CloudInferenceError",
    "LocalInferenceError",
    "create_inference_client",
]
