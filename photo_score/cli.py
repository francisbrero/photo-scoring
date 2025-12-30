"""CLI for photo scoring."""

import logging
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from photo_score.config.loader import get_default_config, load_config
from photo_score.inference.client import OpenRouterClient, OpenRouterError
from photo_score.ingestion.discover import DEFAULT_EXTENSIONS, discover_images
from photo_score.ingestion.metadata import extract_exif
from photo_score.output.csv_writer import write_csv
from photo_score.scoring.explanations import ExplanationGenerator
from photo_score.scoring.reducer import ScoringReducer
from photo_score.storage.cache import Cache
from photo_score.storage.models import ScoringResult, ImageMetadata

app = typer.Typer(
    name="photo-score",
    help="Score photo collections using vision models.",
    add_completion=False,
)


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )


@app.command()
def run(
    input_dir: Annotated[
        Path,
        typer.Option(
            "--input",
            "-i",
            help="Root directory to scan for images.",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ],
    output_file: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output CSV file path.",
            resolve_path=True,
        ),
    ],
    config_file: Annotated[
        Optional[Path],
        typer.Option(
            "--config",
            "-c",
            help="Scoring configuration YAML file.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            resolve_path=True,
        ),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Overwrite output file if it exists.",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose output.",
        ),
    ] = False,
    extensions: Annotated[
        Optional[str],
        typer.Option(
            "--extensions",
            "-e",
            help="Comma-separated list of file extensions (e.g., '.jpg,.png').",
        ),
    ] = None,
) -> None:
    """Score images in a directory and output results to CSV."""
    setup_logging(verbose)
    logger = logging.getLogger(__name__)

    # Check output file
    if output_file.exists() and not overwrite:
        typer.echo(f"Error: Output file {output_file} exists. Use --overwrite to replace.")
        raise typer.Exit(code=1)

    # Load configuration
    if config_file:
        logger.info(f"Loading config from {config_file}")
        config = load_config(config_file)
    else:
        logger.info("Using default configuration")
        config = get_default_config()

    # Parse extensions
    ext_set = None
    if extensions:
        ext_set = {ext.strip().lower() for ext in extensions.split(",")}
        # Ensure extensions have leading dot
        ext_set = {ext if ext.startswith(".") else f".{ext}" for ext in ext_set}
    else:
        ext_set = DEFAULT_EXTENSIONS

    # Discover images
    typer.echo(f"Scanning {input_dir} for images...")
    images = discover_images(input_dir, ext_set)

    if not images:
        typer.echo("No images found.")
        raise typer.Exit(code=0)

    typer.echo(f"Found {len(images)} images.")

    # Initialize components
    cache = Cache()
    reducer = ScoringReducer(config)
    explainer = ExplanationGenerator(config)

    # Process images
    results: list[ScoringResult] = []
    cache_hits = 0
    cache_misses = 0

    try:
        with OpenRouterClient(model_name=config.model.name) as client:
            with typer.progressbar(images, label="Processing images") as progress:
                for image in progress:
                    # Check cache for attributes
                    cached_attrs = cache.get_attributes(image.image_id)

                    if cached_attrs is not None:
                        cache_hits += 1
                        attrs = cached_attrs
                        logger.debug(f"Cache hit: {image.filename}")
                    else:
                        cache_misses += 1
                        logger.debug(f"Cache miss: {image.filename}")

                        try:
                            # Run inference for scoring
                            attrs = client.analyze_image(
                                image.image_id,
                                image.file_path,
                                config.model.version,
                            )
                            # Cache result
                            cache.store_attributes(attrs)
                        except OpenRouterError as e:
                            logger.warning(f"Failed to analyze {image.filename}: {e}")
                            continue

                    # Get or extract metadata
                    cached_metadata = cache.get_metadata(image.image_id)
                    if cached_metadata is not None:
                        metadata = cached_metadata
                    else:
                        # Extract EXIF metadata
                        exif = extract_exif(image.file_path)

                        # Get vision-based metadata (description, location)
                        try:
                            vision_meta = client.analyze_metadata(image.file_path)
                            description = vision_meta.description
                            location_name = vision_meta.location_name
                            location_country = vision_meta.location_country
                        except OpenRouterError as e:
                            logger.warning(f"Failed to get metadata for {image.filename}: {e}")
                            description = None
                            location_name = None
                            location_country = None

                        # Build combined metadata
                        metadata = ImageMetadata(
                            date_taken=exif.get("timestamp") if exif else None,
                            latitude=exif.get("latitude") if exif else None,
                            longitude=exif.get("longitude") if exif else None,
                            description=description,
                            location_name=location_name,
                            location_country=location_country,
                        )

                        # Cache metadata
                        cache.store_metadata(image.image_id, metadata)

                    # Compute scores
                    result = reducer.compute_scores(
                        image.image_id,
                        image.relative_path,
                        attrs,
                    )

                    # Generate explanation
                    result.explanation = explainer.generate(
                        attrs,
                        result.contributions,
                        result.final_score,
                    )

                    # Attach metadata
                    result.metadata = metadata

                    results.append(result)

    except OpenRouterError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        typer.echo("\nInterrupted. Saving partial results...")

    # Write output
    if results:
        write_csv(results, output_file, config)
        typer.echo(f"\nResults written to {output_file}")
        typer.echo(f"Processed: {len(results)} images")
        typer.echo(f"Cache hits: {cache_hits}, Cache misses: {cache_misses}")
    else:
        typer.echo("No results to write.")


@app.command()
def rescore(
    input_dir: Annotated[
        Path,
        typer.Option(
            "--input",
            "-i",
            help="Root directory to scan for images.",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ],
    output_file: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output CSV file path.",
            resolve_path=True,
        ),
    ],
    config_file: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            help="Scoring configuration YAML file.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            resolve_path=True,
        ),
    ],
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Overwrite output file if it exists.",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose output.",
        ),
    ] = False,
) -> None:
    """Re-score images using cached attributes with a new configuration.

    This command does not run inference - it only uses cached attribute data.
    """
    setup_logging(verbose)
    logger = logging.getLogger(__name__)

    # Check output file
    if output_file.exists() and not overwrite:
        typer.echo(f"Error: Output file {output_file} exists. Use --overwrite to replace.")
        raise typer.Exit(code=1)

    # Load configuration
    logger.info(f"Loading config from {config_file}")
    config = load_config(config_file)

    # Discover images
    typer.echo(f"Scanning {input_dir} for images...")
    images = discover_images(input_dir)

    if not images:
        typer.echo("No images found.")
        raise typer.Exit(code=0)

    typer.echo(f"Found {len(images)} images.")

    # Initialize components
    cache = Cache()
    reducer = ScoringReducer(config)
    explainer = ExplanationGenerator(config)

    # Process images from cache only
    results: list[ScoringResult] = []
    missing = 0

    for image in images:
        cached_attrs = cache.get_attributes(image.image_id)

        if cached_attrs is None:
            missing += 1
            logger.debug(f"No cached attributes for {image.filename}")
            continue

        # Compute scores
        result = reducer.compute_scores(
            image.image_id,
            image.relative_path,
            cached_attrs,
        )

        # Generate explanation
        result.explanation = explainer.generate(
            cached_attrs,
            result.contributions,
            result.final_score,
        )

        # Get cached metadata if available
        cached_metadata = cache.get_metadata(image.image_id)
        if cached_metadata is not None:
            result.metadata = cached_metadata

        results.append(result)

    # Write output
    if results:
        write_csv(results, output_file, config)
        typer.echo(f"\nResults written to {output_file}")
        typer.echo(f"Scored: {len(results)} images")
        if missing:
            typer.echo(f"Skipped (no cache): {missing} images")
    else:
        typer.echo("No cached data found. Run 'photo-score run' first.")


@app.command()
def calibrate(
    input_dir: Annotated[
        Path,
        typer.Option(
            "--input",
            "-i",
            help="Directory containing images to calibrate on.",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ],
    output_file: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output CSV file for calibration results.",
            resolve_path=True,
        ),
    ],
    max_images: Annotated[
        Optional[int],
        typer.Option(
            "--max-images",
            "-n",
            help="Maximum number of images to test.",
        ),
    ] = 10,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose output.",
        ),
    ] = False,
) -> None:
    """Calibrate composite scoring using multiple vision models.

    Uses Pixtral for feature extraction and combines scores from
    Qwen, GPT-4o-mini, and Gemini for a weighted composite score.
    """
    import csv
    import json

    from photo_score.scoring.composite import CompositeScorer

    setup_logging(verbose)
    logger = logging.getLogger(__name__)

    # Discover images
    typer.echo(f"Scanning {input_dir} for images...")
    images = discover_images(input_dir)
    if max_images:
        images = images[:max_images]

    if not images:
        typer.echo("No images found.")
        raise typer.Exit(code=0)

    typer.echo(f"Found {len(images)} images for calibration.")
    typer.echo(f"Each image requires 8 API calls (feature extraction + 3 aesthetic + 3 technical + metadata)")
    typer.echo(f"Total API calls: {len(images) * 8}\n")

    scorer = CompositeScorer()
    results = []

    try:
        for i, image in enumerate(images):
            typer.echo(f"\n[{i+1}/{len(images)}] Processing {image.filename}...")

            result = scorer.score_image(image.file_path, include_features=True)
            results.append(result)

            # Print summary
            typer.echo(f"  Final Score: {result.final_score:.1f}/100")
            typer.echo(f"  Aesthetic: {result.aesthetic_score:.3f} | Technical: {result.technical_score:.3f}")
            typer.echo(f"  Scene: {result.features.scene_type} | Lighting: {result.features.lighting}")

            # Show model agreement
            aes_scores = [f"{s.model_id.split('/')[-1][:8]}={((s.composition+s.subject_strength+s.visual_appeal)/3):.2f}"
                          for s in result.aesthetic_scores if s.success]
            typer.echo(f"  Model scores: {', '.join(aes_scores)}")

    except KeyboardInterrupt:
        typer.echo("\nInterrupted. Saving partial results...")
    finally:
        scorer.close()

    # Save results
    if results:
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "image_path", "final_score", "aesthetic_score", "technical_score",
                "composition", "subject_strength", "visual_appeal",
                "sharpness", "exposure", "noise_level",
                "scene_type", "lighting", "subject_position",
                "description", "location_name", "location_country",
                "qwen_aesthetic", "gpt4o_aesthetic", "gemini_aesthetic",
                "features_json",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for r in results:
                qwen = next((s for s in r.aesthetic_scores if "qwen" in s.model_id), None)
                gpt = next((s for s in r.aesthetic_scores if "gpt" in s.model_id), None)
                gem = next((s for s in r.aesthetic_scores if "gemini" in s.model_id), None)

                writer.writerow({
                    "image_path": r.image_path,
                    "final_score": round(r.final_score, 2),
                    "aesthetic_score": round(r.aesthetic_score, 3),
                    "technical_score": round(r.technical_score, 3),
                    "composition": round(r.composition, 3),
                    "subject_strength": round(r.subject_strength, 3),
                    "visual_appeal": round(r.visual_appeal, 3),
                    "sharpness": round(r.sharpness, 3),
                    "exposure": round(r.exposure, 3),
                    "noise_level": round(r.noise_level, 3),
                    "scene_type": r.features.scene_type,
                    "lighting": r.features.lighting,
                    "subject_position": r.features.subject_position,
                    "description": r.description,
                    "location_name": r.location_name,
                    "location_country": r.location_country,
                    "qwen_aesthetic": f"{qwen.composition:.2f}/{qwen.subject_strength:.2f}/{qwen.visual_appeal:.2f}" if qwen and qwen.success else "",
                    "gpt4o_aesthetic": f"{gpt.composition:.2f}/{gpt.subject_strength:.2f}/{gpt.visual_appeal:.2f}" if gpt and gpt.success else "",
                    "gemini_aesthetic": f"{gem.composition:.2f}/{gem.subject_strength:.2f}/{gem.visual_appeal:.2f}" if gem and gem.success else "",
                    "features_json": json.dumps(r.features.raw),
                })

        typer.echo(f"\nResults saved to {output_file}")

        # Summary statistics
        scores = [r.final_score for r in results]
        typer.echo(f"\nScore Distribution:")
        typer.echo(f"  Min: {min(scores):.1f} | Max: {max(scores):.1f} | Avg: {sum(scores)/len(scores):.1f}")

        bins = [(0, 30, "Flawed"), (30, 50, "Tourist"), (50, 70, "Competent"), (70, 85, "Strong"), (85, 100, "Excellent")]
        for low, high, label in bins:
            count = sum(1 for s in scores if low <= s < high)
            if count:
                typer.echo(f"  {label} ({low}-{high}): {count} images")


@app.command()
def benchmark(
    input_dir: Annotated[
        Path,
        typer.Option(
            "--input",
            "-i",
            help="Directory containing images to benchmark.",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ],
    output_file: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output CSV file for benchmark results.",
            resolve_path=True,
        ),
    ],
    models: Annotated[
        Optional[str],
        typer.Option(
            "--models",
            "-m",
            help="Comma-separated list of model keys to benchmark. Use 'list' to see available models.",
        ),
    ] = None,
    tasks: Annotated[
        Optional[str],
        typer.Option(
            "--tasks",
            "-t",
            help="Comma-separated tasks to run: aesthetic,technical,metadata. Default: all.",
        ),
    ] = None,
    max_images: Annotated[
        Optional[int],
        typer.Option(
            "--max-images",
            "-n",
            help="Maximum number of images to test.",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose output.",
        ),
    ] = False,
) -> None:
    """Benchmark multiple vision models on photo scoring tasks.

    Compare different models' scoring behavior, latency, and cost.
    """
    from photo_score.benchmark.models import VISION_MODELS, DEFAULT_BENCHMARK_MODELS
    from photo_score.benchmark.runner import BenchmarkRunner

    setup_logging(verbose)

    # Handle 'list' command
    if models == "list":
        typer.echo("\nAvailable vision models for benchmarking:\n")
        typer.echo(f"{'Key':<20} {'Name':<25} {'Input $/M':<12} {'Output $/M':<12}")
        typer.echo("-" * 70)
        for key, config in VISION_MODELS.items():
            typer.echo(f"{key:<20} {config.name:<25} ${config.input_cost_per_m:<11.3f} ${config.output_cost_per_m:<11.3f}")
        typer.echo(f"\nDefault models: {', '.join(DEFAULT_BENCHMARK_MODELS)}")
        return

    # Parse models
    if models:
        model_keys = [m.strip() for m in models.split(",")]
    else:
        model_keys = DEFAULT_BENCHMARK_MODELS

    # Parse tasks
    task_list = None
    if tasks:
        task_list = [t.strip() for t in tasks.split(",")]

    typer.echo(f"Benchmarking models: {', '.join(model_keys)}")
    typer.echo(f"Tasks: {task_list or ['aesthetic', 'technical', 'metadata']}")
    typer.echo(f"Image directory: {input_dir}")

    runner = BenchmarkRunner()
    result = runner.run_benchmark(
        image_dir=input_dir,
        model_keys=model_keys,
        tasks=task_list,
        max_images=max_images,
    )

    runner.save_results(result, output_file)
    runner.print_summary(result)


if __name__ == "__main__":
    app()
