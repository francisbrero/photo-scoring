"""Vision model configurations for benchmarking."""

from dataclasses import dataclass


@dataclass
class ModelConfig:
    """Configuration for a vision model."""

    id: str
    name: str
    input_cost_per_m: float  # $ per million tokens
    output_cost_per_m: float  # $ per million tokens
    supports_vision: bool = True
    notes: str = ""


# Available vision models on OpenRouter (sorted by cost)
VISION_MODELS = {
    "qwen2.5-vl-72b": ModelConfig(
        id="qwen/qwen2.5-vl-72b-instruct",
        name="Qwen 2.5 VL 72B",
        input_cost_per_m=0.07,
        output_cost_per_m=0.26,
        notes="Best value. Strong at recognizing objects, text, charts.",
    ),
    "seed-1.6-flash": ModelConfig(
        id="bytedance-seed/seed-1.6-flash",
        name="ByteDance Seed 1.6 Flash",
        input_cost_per_m=0.075,
        output_cost_per_m=0.30,
        notes="Fast, supports text/image/video.",
    ),
    "pixtral-12b": ModelConfig(
        id="mistralai/pixtral-12b",
        name="Pixtral 12B",
        input_cost_per_m=0.10,
        output_cost_per_m=0.10,
        notes="Mistral's first multimodal. Very cheap output.",
    ),
    "gpt-4o-mini": ModelConfig(
        id="openai/gpt-4o-mini",
        name="GPT-4o Mini",
        input_cost_per_m=0.15,
        output_cost_per_m=0.60,
        notes="OpenAI's efficient multimodal model.",
    ),
    "grok-4-fast": ModelConfig(
        id="x-ai/grok-4-fast",
        name="Grok 4 Fast",
        input_cost_per_m=0.20,
        output_cost_per_m=0.50,
        notes="xAI's fast vision model. 2M context.",
    ),
    "qwen3-vl-235b": ModelConfig(
        id="qwen/qwen3-vl-235b-a22b-instruct",
        name="Qwen3 VL 235B",
        input_cost_per_m=0.20,
        output_cost_per_m=1.20,
        notes="Largest Qwen vision model. Best quality from Qwen.",
    ),
    "claude-3-haiku": ModelConfig(
        id="anthropic/claude-3-haiku",
        name="Claude 3 Haiku",
        input_cost_per_m=0.25,
        output_cost_per_m=1.25,
        notes="Fast Anthropic model.",
    ),
    "gemini-2.5-flash": ModelConfig(
        id="google/gemini-2.5-flash",
        name="Gemini 2.5 Flash",
        input_cost_per_m=0.30,
        output_cost_per_m=2.50,
        notes="Google's fast multimodal.",
    ),
    "claude-3.5-sonnet": ModelConfig(
        id="anthropic/claude-3.5-sonnet",
        name="Claude 3.5 Sonnet",
        input_cost_per_m=3.00,
        output_cost_per_m=15.00,
        notes="High quality, expensive. Current baseline.",
    ),
}

# Default models to benchmark (balanced cost/quality)
DEFAULT_BENCHMARK_MODELS = [
    "qwen2.5-vl-72b",  # Cheapest
    "pixtral-12b",  # Very cheap, Mistral
    "gpt-4o-mini",  # OpenAI baseline
    "gemini-2.5-flash",  # Google
    "claude-3.5-sonnet",  # Current baseline (expensive)
]
