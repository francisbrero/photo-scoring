#!/usr/bin/env python3
"""Calibration script for composite scoring system.

Run on sample images to compare composite scores vs Claude baseline.
"""

import csv
import json
import logging
import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from photo_score.scoring.composite import CompositeScorer, CompositeResult
from photo_score.ingestion.discover import discover_images

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_calibration(image_dir: Path, output_path: Path, max_images: int = 10):
    """Run calibration on sample images."""

    # Discover images
    images = discover_images(image_dir)[:max_images]
    logger.info(f"Found {len(images)} images for calibration")

    scorer = CompositeScorer()
    results: list[CompositeResult] = []

    try:
        for i, image in enumerate(images):
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing [{i+1}/{len(images)}]: {image.filename}")
            logger.info(f"{'='*60}")

            result = scorer.score_image(image.file_path, include_features=True)
            results.append(result)

            # Print summary for this image
            print(f"\n{image.filename}:")
            print(f"  Final Score: {result.final_score:.1f}/100")
            print(f"  Aesthetic: {result.aesthetic_score:.3f} (comp={result.composition:.2f}, subj={result.subject_strength:.2f}, appeal={result.visual_appeal:.2f})")
            print(f"  Technical: {result.technical_score:.3f} (sharp={result.sharpness:.2f}, exp={result.exposure:.2f}, noise={result.noise_level:.2f})")
            print(f"  Features: {result.features.scene_type}, {result.features.lighting}, {result.features.subject_position}")
            print(f"  Location: {result.location_name or 'Unknown'}, {result.location_country or 'Unknown'}")

            # Show individual model scores
            print(f"  Aesthetic scores by model:")
            for score in result.aesthetic_scores:
                if score.success:
                    model_short = score.model_id.split("/")[-1][:15]
                    print(f"    {model_short}: comp={score.composition:.2f}, subj={score.subject_strength:.2f}, appeal={score.visual_appeal:.2f}")

    finally:
        scorer.close()

    # Save detailed results to CSV
    save_calibration_results(results, output_path)

    # Print summary statistics
    print_summary(results)

    return results


def save_calibration_results(results: list[CompositeResult], output_path: Path):
    """Save calibration results to CSV."""

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "image_path",
            "final_score",
            "aesthetic_score",
            "technical_score",
            "composition",
            "subject_strength",
            "visual_appeal",
            "sharpness",
            "exposure",
            "noise_level",
            "scene_type",
            "lighting",
            "subject_position",
            "description",
            "location_name",
            "location_country",
            "explanation",
            "improvements",
            "qwen_aesthetic",
            "gpt4o_aesthetic",
            "gemini_aesthetic",
            "qwen_technical",
            "gpt4o_technical",
            "gemini_technical",
            "features_json",
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            # Extract individual model scores
            qwen_aes = next((s for s in result.aesthetic_scores if "qwen" in s.model_id), None)
            gpt_aes = next((s for s in result.aesthetic_scores if "gpt" in s.model_id), None)
            gem_aes = next((s for s in result.aesthetic_scores if "gemini" in s.model_id), None)

            qwen_tech = next((s for s in result.technical_scores if "qwen" in s.model_id), None)
            gpt_tech = next((s for s in result.technical_scores if "gpt" in s.model_id), None)
            gem_tech = next((s for s in result.technical_scores if "gemini" in s.model_id), None)

            def avg_score(s):
                if s and s.success:
                    return (s.composition + s.subject_strength + s.visual_appeal) / 3 if hasattr(s, 'composition') and s.composition else (s.sharpness + s.exposure + s.noise_level) / 3
                return None

            row = {
                "image_path": result.image_path,
                "final_score": round(result.final_score, 2),
                "aesthetic_score": round(result.aesthetic_score, 3),
                "technical_score": round(result.technical_score, 3),
                "composition": round(result.composition, 3),
                "subject_strength": round(result.subject_strength, 3),
                "visual_appeal": round(result.visual_appeal, 3),
                "sharpness": round(result.sharpness, 3),
                "exposure": round(result.exposure, 3),
                "noise_level": round(result.noise_level, 3),
                "scene_type": result.features.scene_type,
                "lighting": result.features.lighting,
                "subject_position": result.features.subject_position,
                "description": result.description,
                "location_name": result.location_name,
                "location_country": result.location_country,
                "explanation": result.explanation,
                "improvements": " | ".join(result.improvements),
                "qwen_aesthetic": f"{qwen_aes.composition:.2f}/{qwen_aes.subject_strength:.2f}/{qwen_aes.visual_appeal:.2f}" if qwen_aes and qwen_aes.success else "failed",
                "gpt4o_aesthetic": f"{gpt_aes.composition:.2f}/{gpt_aes.subject_strength:.2f}/{gpt_aes.visual_appeal:.2f}" if gpt_aes and gpt_aes.success else "failed",
                "gemini_aesthetic": f"{gem_aes.composition:.2f}/{gem_aes.subject_strength:.2f}/{gem_aes.visual_appeal:.2f}" if gem_aes and gem_aes.success else "failed",
                "qwen_technical": f"{qwen_tech.sharpness:.2f}/{qwen_tech.exposure:.2f}/{qwen_tech.noise_level:.2f}" if qwen_tech and qwen_tech.success else "failed",
                "gpt4o_technical": f"{gpt_tech.sharpness:.2f}/{gpt_tech.exposure:.2f}/{gpt_tech.noise_level:.2f}" if gpt_tech and gpt_tech.success else "failed",
                "gemini_technical": f"{gem_tech.sharpness:.2f}/{gem_tech.exposure:.2f}/{gem_tech.noise_level:.2f}" if gem_tech and gem_tech.success else "failed",
                "features_json": json.dumps(result.features.raw),
            }
            writer.writerow(row)

    logger.info(f"Results saved to {output_path}")


def print_summary(results: list[CompositeResult]):
    """Print summary statistics."""

    print("\n" + "=" * 60)
    print("CALIBRATION SUMMARY")
    print("=" * 60)

    scores = [r.final_score for r in results]
    aesthetics = [r.aesthetic_score for r in results]
    technicals = [r.technical_score for r in results]

    print(f"\nFinal Scores:")
    print(f"  Min: {min(scores):.1f}")
    print(f"  Max: {max(scores):.1f}")
    print(f"  Avg: {sum(scores)/len(scores):.1f}")

    print(f"\nScore Distribution:")
    bins = [(0, 30), (30, 50), (50, 70), (70, 85), (85, 100)]
    labels = ["Flawed (0-30)", "Tourist (30-50)", "Competent (50-70)", "Strong (70-85)", "Excellent (85-100)"]
    for (low, high), label in zip(bins, labels):
        count = sum(1 for s in scores if low <= s < high)
        print(f"  {label}: {count} images")

    print(f"\nModel Agreement (aesthetic scores):")
    for result in results[:3]:  # Show first 3
        scores_by_model = []
        for s in result.aesthetic_scores:
            if s.success:
                avg = (s.composition + s.subject_strength + s.visual_appeal) / 3
                model_name = s.model_id.split("/")[-1][:10]
                scores_by_model.append(f"{model_name}={avg:.2f}")
        print(f"  {result.image_path}: {', '.join(scores_by_model)}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Calibrate composite scoring system")
    parser.add_argument("-i", "--input", required=True, help="Image directory")
    parser.add_argument("-o", "--output", default="calibration_results.csv", help="Output CSV")
    parser.add_argument("-n", "--max-images", type=int, default=10, help="Max images to process")

    args = parser.parse_args()

    # Load API key from .env
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("OPENROUTER_API_KEY="):
                    os.environ["OPENROUTER_API_KEY"] = line.split("=", 1)[1].strip()

    run_calibration(
        image_dir=Path(args.input),
        output_path=Path(args.output),
        max_images=args.max_images,
    )
