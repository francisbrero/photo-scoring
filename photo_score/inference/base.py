"""Inference client protocol."""

from pathlib import Path
from typing import Protocol, runtime_checkable

from photo_score.inference.schemas import MetadataResponse
from photo_score.storage.models import NormalizedAttributes


@runtime_checkable
class InferenceClient(Protocol):
    """Protocol for inference backends (cloud or local)."""

    model_name: str
    model_version: str

    def analyze_image(
        self, image_id: str, image_path: Path, model_version: str
    ) -> NormalizedAttributes: ...

    def analyze_metadata(self, image_path: Path) -> MetadataResponse: ...

    def close(self) -> None: ...

    def __enter__(self) -> "InferenceClient": ...

    def __exit__(self, *args) -> None: ...
