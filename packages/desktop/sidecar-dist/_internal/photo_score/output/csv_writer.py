"""CSV output generation."""

import csv
import json
from pathlib import Path

from photo_score.config.schema import ScoringConfig
from photo_score.storage.models import ScoringResult


def write_csv(
    results: list[ScoringResult],
    output_path: Path,
    config: ScoringConfig,
    include_config_version: bool = True,
) -> None:
    """Write scoring results to CSV file.

    Args:
        results: List of scoring results to write.
        output_path: Path to output CSV file.
        config: Scoring configuration used.
        include_config_version: Whether to include config version column.
    """
    # Sort by final score descending
    sorted_results = sorted(results, key=lambda r: r.final_score, reverse=True)

    # Define columns
    fieldnames = [
        "image_path",
        "final_score",
        "technical_score",
        "aesthetic_score",
        "attributes",
        "explanation",
        "date_taken",
        "description",
        "location_name",
        "location_country",
        "latitude",
        "longitude",
    ]

    if include_config_version:
        fieldnames.append("config_version")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()

        for result in sorted_results:
            # Serialize attributes to JSON
            attrs_dict = {
                "composition": result.attributes.composition,
                "subject_strength": result.attributes.subject_strength,
                "visual_appeal": result.attributes.visual_appeal,
                "sharpness": result.attributes.sharpness,
                "exposure_balance": result.attributes.exposure_balance,
                "noise_level": result.attributes.noise_level,
            }

            row = {
                "image_path": result.image_path,
                "final_score": result.final_score,
                "technical_score": result.technical_score,
                "aesthetic_score": result.aesthetic_score,
                "attributes": json.dumps(attrs_dict),
                "explanation": result.explanation,
                "date_taken": "",
                "description": "",
                "location_name": "",
                "location_country": "",
                "latitude": "",
                "longitude": "",
            }

            # Add metadata if present
            if result.metadata:
                meta = result.metadata
                if meta.date_taken:
                    row["date_taken"] = meta.date_taken.strftime("%Y-%m-%d %H:%M:%S")
                if meta.description:
                    row["description"] = meta.description
                if meta.location_name:
                    row["location_name"] = meta.location_name
                if meta.location_country:
                    row["location_country"] = meta.location_country
                if meta.latitude is not None:
                    row["latitude"] = f"{meta.latitude:.6f}"
                if meta.longitude is not None:
                    row["longitude"] = f"{meta.longitude:.6f}"

            if include_config_version:
                row["config_version"] = config.version

            writer.writerow(row)
