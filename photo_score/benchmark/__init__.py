"""Benchmark module for comparing vision models.

This module provides tools for benchmarking different vision models
on photo scoring tasks.

Main exports:
- BenchmarkRunner: Run benchmarks across models and images
- VISION_MODELS: Available vision models for benchmarking
- DEFAULT_BENCHMARK_MODELS: Default models to benchmark
"""

from photo_score.benchmark.runner import BenchmarkRunner
from photo_score.benchmark.models import VISION_MODELS, DEFAULT_BENCHMARK_MODELS

__all__ = ["BenchmarkRunner", "VISION_MODELS", "DEFAULT_BENCHMARK_MODELS"]
