"""Benchmark runner for comparing vision models on photo scoring."""

import csv
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from photo_score.benchmark.models import VISION_MODELS, ModelConfig
from photo_score.inference.client import OpenRouterClient, OpenRouterError
from photo_score.inference.prompts import (
    AESTHETIC_PROMPT,
    TECHNICAL_PROMPT,
    METADATA_PROMPT,
)
from photo_score.ingestion.discover import discover_images

logger = logging.getLogger(__name__)


@dataclass
class ModelResult:
    """Result from a single model on a single image."""

    model_id: str
    model_name: str
    image_path: str
    task: str  # "aesthetic", "technical", "metadata"
    success: bool
    response: dict = field(default_factory=dict)
    error: str = ""
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class BenchmarkResult:
    """Complete benchmark results."""

    started_at: datetime
    completed_at: datetime | None = None
    models: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    results: list[ModelResult] = field(default_factory=list)


class BenchmarkRunner:
    """Run benchmarks comparing multiple vision models."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self.client = OpenRouterClient(api_key=api_key)

    def run_single_task(
        self,
        image_path: Path,
        model_config: ModelConfig,
        task: str,
        prompt: str,
    ) -> ModelResult:
        """Run a single task (aesthetic/technical/metadata) on one image with one model."""
        result = ModelResult(
            model_id=model_config.id,
            model_name=model_config.name,
            image_path=str(image_path.name),
            task=task,
            success=False,
        )

        start_time = time.time()
        try:
            response = self.client.call_api(image_path, prompt, model=model_config.id)
            result.success = True
            result.response = response
        except OpenRouterError as e:
            result.error = str(e)
        except Exception as e:
            result.error = f"Unexpected error: {e}"

        result.latency_ms = (time.time() - start_time) * 1000
        return result

    def run_benchmark(
        self,
        image_dir: Path,
        model_keys: list[str],
        tasks: list[str] | None = None,
        max_images: int | None = None,
    ) -> BenchmarkResult:
        """Run full benchmark across models and images.

        Args:
            image_dir: Directory containing images to test.
            model_keys: List of model keys from VISION_MODELS.
            tasks: List of tasks to run ("aesthetic", "technical", "metadata").
                   Defaults to all three.
            max_images: Maximum number of images to test.

        Returns:
            BenchmarkResult with all results.
        """
        if tasks is None:
            tasks = ["aesthetic", "technical", "metadata"]

        task_prompts = {
            "aesthetic": AESTHETIC_PROMPT,
            "technical": TECHNICAL_PROMPT,
            "metadata": METADATA_PROMPT,
        }

        # Discover images
        images = discover_images(image_dir)
        if max_images:
            images = images[:max_images]

        # Validate models
        models = []
        for key in model_keys:
            if key not in VISION_MODELS:
                logger.warning(f"Unknown model key: {key}")
                continue
            models.append(VISION_MODELS[key])

        benchmark = BenchmarkResult(
            started_at=datetime.now(),
            models=[m.id for m in models],
            images=[img.filename for img in images],
        )

        total_tasks = len(images) * len(models) * len(tasks)
        completed = 0

        logger.info(
            f"Starting benchmark: {len(images)} images x {len(models)} models x {len(tasks)} tasks = {total_tasks} API calls"
        )

        for image in images:
            for model in models:
                for task in tasks:
                    completed += 1
                    logger.info(
                        f"[{completed}/{total_tasks}] {model.name} - {image.filename} - {task}"
                    )

                    result = self.run_single_task(
                        image.file_path,
                        model,
                        task,
                        task_prompts[task],
                    )
                    benchmark.results.append(result)

                    # Small delay to avoid rate limiting
                    time.sleep(0.5)

        benchmark.completed_at = datetime.now()
        return benchmark

    def save_results(self, benchmark: BenchmarkResult, output_path: Path) -> None:
        """Save benchmark results to CSV."""
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "model_id",
                    "model_name",
                    "image_path",
                    "task",
                    "success",
                    "latency_ms",
                    "response",
                    "error",
                ],
            )
            writer.writeheader()
            for result in benchmark.results:
                writer.writerow(
                    {
                        "model_id": result.model_id,
                        "model_name": result.model_name,
                        "image_path": result.image_path,
                        "task": result.task,
                        "success": result.success,
                        "latency_ms": round(result.latency_ms, 2),
                        "response": json.dumps(result.response)
                        if result.response
                        else "",
                        "error": result.error,
                    }
                )

        logger.info(f"Results saved to {output_path}")

    def print_summary(self, benchmark: BenchmarkResult) -> None:
        """Print summary statistics."""
        print("\n" + "=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)

        duration = (benchmark.completed_at - benchmark.started_at).total_seconds()
        print(f"Duration: {duration:.1f}s")
        print(f"Images: {len(benchmark.images)}")
        print(f"Models: {len(benchmark.models)}")
        print(f"Total API calls: {len(benchmark.results)}")

        # Group by model
        model_stats: dict[str, dict[str, Any]] = {}
        for result in benchmark.results:
            if result.model_name not in model_stats:
                model_stats[result.model_name] = {
                    "success": 0,
                    "failure": 0,
                    "total_latency": 0.0,
                    "tasks": {},
                }

            stats = model_stats[result.model_name]
            if result.success:
                stats["success"] += 1
            else:
                stats["failure"] += 1
            stats["total_latency"] += result.latency_ms

            if result.task not in stats["tasks"]:
                stats["tasks"][result.task] = {"success": 0, "responses": []}
            if result.success:
                stats["tasks"][result.task]["success"] += 1
                stats["tasks"][result.task]["responses"].append(result.response)

        print("\n" + "-" * 60)
        print("BY MODEL:")
        print("-" * 60)

        for model_name, stats in model_stats.items():
            total = stats["success"] + stats["failure"]
            success_rate = (stats["success"] / total * 100) if total > 0 else 0
            avg_latency = stats["total_latency"] / total if total > 0 else 0

            print(f"\n{model_name}:")
            print(f"  Success rate: {success_rate:.1f}% ({stats['success']}/{total})")
            print(f"  Avg latency: {avg_latency:.0f}ms")

            # Show sample scores for aesthetic task
            if (
                "aesthetic" in stats["tasks"]
                and stats["tasks"]["aesthetic"]["responses"]
            ):
                responses = stats["tasks"]["aesthetic"]["responses"]
                if responses:
                    avg_composition = sum(
                        r.get("composition", 0) for r in responses
                    ) / len(responses)
                    avg_subject = sum(
                        r.get("subject_strength", 0) for r in responses
                    ) / len(responses)
                    avg_appeal = sum(
                        r.get("visual_appeal", 0) for r in responses
                    ) / len(responses)
                    print(
                        f"  Avg aesthetic scores: composition={avg_composition:.2f}, subject={avg_subject:.2f}, appeal={avg_appeal:.2f}"
                    )

        print("\n" + "=" * 60)
