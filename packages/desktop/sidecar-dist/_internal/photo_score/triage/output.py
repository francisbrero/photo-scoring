"""Output handling for triage results.

Creates symlink folders containing selected photos.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def create_selection_folder(
    selected_paths: list[Path],
    output_dir: Path,
    overwrite: bool = False,
) -> int:
    """Create a folder with symlinks to selected photos.

    Args:
        selected_paths: List of paths to selected photos.
        output_dir: Directory to create symlinks in.
        overwrite: If True, remove existing output directory.

    Returns:
        Number of symlinks created.

    Raises:
        FileExistsError: If output_dir exists and overwrite is False.
    """
    if output_dir.exists():
        if overwrite:
            # Remove existing symlinks but preserve the directory
            for item in output_dir.iterdir():
                if item.is_symlink():
                    item.unlink()
                elif item.is_file():
                    item.unlink()
            logger.info(f"Cleared existing output directory: {output_dir}")
        else:
            raise FileExistsError(
                f"Output directory already exists: {output_dir}. "
                "Use --overwrite to replace."
            )
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created output directory: {output_dir}")

    created = 0
    used_names: dict[str, int] = {}

    for source_path in selected_paths:
        # Get unique filename (handle collisions)
        base_name = source_path.name
        name_key = base_name.lower()

        if name_key in used_names:
            # Add suffix for collision
            used_names[name_key] += 1
            stem = source_path.stem
            suffix = source_path.suffix
            link_name = f"{stem}_{used_names[name_key]}{suffix}"
        else:
            used_names[name_key] = 0
            link_name = base_name

        link_path = output_dir / link_name

        try:
            # Create symlink (use absolute path for source)
            os.symlink(source_path.resolve(), link_path)
            created += 1
            logger.debug(f"Created symlink: {link_name} -> {source_path}")
        except OSError as e:
            logger.warning(f"Failed to create symlink for {source_path}: {e}")

    logger.info(f"Created {created} symlinks in {output_dir}")
    return created


def create_selection_manifest(
    selected_paths: list[Path],
    output_path: Path,
    input_dir: Path | None = None,
) -> None:
    """Create a text manifest file listing selected photos.

    Args:
        selected_paths: List of paths to selected photos.
        output_path: Path to the manifest file.
        input_dir: If provided, paths are written relative to this directory.
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Triage Selection Manifest\n")
        f.write(f"# Total: {len(selected_paths)} photos\n\n")

        for path in selected_paths:
            if input_dir:
                try:
                    rel_path = path.relative_to(input_dir)
                    f.write(f"{rel_path}\n")
                except ValueError:
                    f.write(f"{path}\n")
            else:
                f.write(f"{path}\n")

    logger.info(f"Wrote manifest with {len(selected_paths)} entries to {output_path}")
