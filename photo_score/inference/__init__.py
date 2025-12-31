"""Vision model inference via OpenRouter.

This module provides the API client for making vision model calls
to OpenRouter for photo analysis.

Main exports:
- OpenRouterClient: HTTP client for vision model API calls
- OpenRouterError: Exception for API errors
"""

from photo_score.inference.client import OpenRouterClient, OpenRouterError

__all__ = ["OpenRouterClient", "OpenRouterError"]
