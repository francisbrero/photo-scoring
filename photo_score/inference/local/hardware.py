"""Hardware capability detection for local inference."""

from dataclasses import dataclass


@dataclass
class HardwareCapabilities:
    """Detected hardware capabilities."""

    has_cuda: bool
    has_mps: bool
    cuda_vram_gb: float | None
    device: str  # "cuda", "mps", or "cpu"
    can_run_local: bool


# Qwen2-VL-2B minimum VRAM requirements
MIN_CUDA_VRAM_GB = 4.0  # 4-bit quantization


def detect_capabilities() -> HardwareCapabilities:
    """Detect hardware capabilities for local inference.

    Checks for CUDA and MPS (Apple Silicon) support.
    Qwen2-VL-2B needs ~4GB VRAM (4-bit) or ~4GB unified memory (fp16 on MPS).
    """
    has_cuda = False
    has_mps = False
    cuda_vram_gb = None

    try:
        import torch

        has_cuda = torch.cuda.is_available()
        if has_cuda:
            props = torch.cuda.get_device_properties(0)
            cuda_vram_gb = props.total_memory / (1024**3)

        has_mps = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    except ImportError:
        pass

    # Determine best device
    if has_cuda and cuda_vram_gb is not None and cuda_vram_gb >= MIN_CUDA_VRAM_GB:
        device = "cuda"
        can_run = True
    elif has_mps:
        device = "mps"
        can_run = True
    else:
        device = "cpu"
        can_run = False

    return HardwareCapabilities(
        has_cuda=has_cuda,
        has_mps=has_mps,
        cuda_vram_gb=cuda_vram_gb,
        device=device,
        can_run_local=can_run,
    )
