"""Model download and management for local inference."""

import shutil
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL_DIR = Path.home() / ".photo_score" / "models"
LOCAL_MODEL_ID = "Qwen/Qwen2-VL-2B-Instruct"


@dataclass
class LocalModelInfo:
    """Info about a downloaded local model."""

    model_id: str
    path: Path
    size_gb: float


class ModelManager:
    """Manage local model downloads."""

    def __init__(self, model_dir: Path | None = None):
        self.model_dir = model_dir or DEFAULT_MODEL_DIR
        self.model_id = LOCAL_MODEL_ID

    def _model_path(self, model_id: str | None = None) -> Path:
        """Get the expected path for a model."""
        mid = model_id or self.model_id
        # Convert "Qwen/Qwen2-VL-2B-Instruct" -> "Qwen--Qwen2-VL-2B-Instruct"
        safe_name = mid.replace("/", "--")
        return self.model_dir / safe_name

    def is_model_available(self, model_id: str | None = None) -> bool:
        """Check if a model is downloaded."""
        path = self._model_path(model_id)
        # Check for config.json as a marker that download completed
        return (path / "config.json").exists()

    def get_model_path(self, model_id: str | None = None) -> Path | None:
        """Get the path to a downloaded model, or None if not available."""
        path = self._model_path(model_id)
        if self.is_model_available(model_id):
            return path
        return None

    def download_model(
        self,
        model_id: str | None = None,
        progress_callback=None,
    ) -> Path:
        """Download a model from Hugging Face Hub.

        Returns:
            Path to the downloaded model directory.
        """
        from huggingface_hub import snapshot_download

        mid = model_id or self.model_id
        path = self._model_path(mid)
        path.parent.mkdir(parents=True, exist_ok=True)

        snapshot_download(
            repo_id=mid,
            local_dir=str(path),
        )

        return path

    def list_models(self) -> list[LocalModelInfo]:
        """List all downloaded models."""
        if not self.model_dir.exists():
            return []

        models = []
        for entry in self.model_dir.iterdir():
            if entry.is_dir() and (entry / "config.json").exists():
                # Calculate size
                total_size = sum(
                    f.stat().st_size for f in entry.rglob("*") if f.is_file()
                )
                size_gb = total_size / (1024**3)
                # Convert "Qwen--Qwen2-VL-2B-Instruct" back to "Qwen/Qwen2-VL-2B-Instruct"
                model_id = entry.name.replace("--", "/")
                models.append(
                    LocalModelInfo(
                        model_id=model_id,
                        path=entry,
                        size_gb=size_gb,
                    )
                )
        return models

    def delete_model(self, model_id: str | None = None) -> None:
        """Delete a downloaded model."""
        path = self._model_path(model_id)
        if path.exists():
            shutil.rmtree(path)
