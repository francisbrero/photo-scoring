"""Tests for grid-based visual triage."""

from pathlib import Path

import pytest
from PIL import Image

from photo_score.triage.grid import GridGenerator, ROW_LABELS
from photo_score.triage.prompts import (
    build_coarse_prompt,
    build_fine_prompt,
    get_criteria_description,
    CRITERIA_STANDOUT,
    CRITERIA_QUALITY,
)
from photo_score.triage.output import create_selection_folder
from photo_score.triage.selector import TriageSelector, COORD_PATTERN


class TestGridGenerator:
    """Tests for grid image generation."""

    @pytest.fixture
    def temp_images(self, tmp_path: Path) -> list[Path]:
        """Create temporary test images."""
        images = []
        for i in range(25):  # Create 25 images for a 5x5 grid
            img_path = tmp_path / f"image_{i:03d}.jpg"
            img = Image.new("RGB", (100, 100), color=(i * 10, i * 10, i * 10))
            img.save(img_path, "JPEG")
            images.append(img_path)
        return images

    def test_generate_single_grid(self, temp_images: list[Path]) -> None:
        """Test generating a single grid from images."""
        generator = GridGenerator(grid_size=5, thumbnail_size=50)
        grids = generator.generate_grids(temp_images)

        assert len(grids) == 1
        grid = grids[0]

        assert grid.rows == 5
        assert grid.cols == 5
        assert grid.total_photos == 25
        assert len(grid.coord_to_path) == 25

        # Check coordinate mapping
        assert "A1" in grid.coord_to_path
        assert "E5" in grid.coord_to_path
        assert grid.coord_to_path["A1"] == temp_images[0]

    def test_generate_multiple_grids(self, tmp_path: Path) -> None:
        """Test generating multiple grids when images exceed grid capacity."""
        # Create 20 images
        images = []
        for i in range(20):
            img_path = tmp_path / f"image_{i:03d}.jpg"
            img = Image.new("RGB", (50, 50), color=(100, 100, 100))
            img.save(img_path, "JPEG")
            images.append(img_path)

        # Use 3x3 grid (9 per grid) -> should create 3 grids
        generator = GridGenerator(grid_size=3, thumbnail_size=30)
        grids = generator.generate_grids(images)

        assert len(grids) == 3
        assert grids[0].total_photos == 9
        assert grids[1].total_photos == 9
        assert grids[2].total_photos == 2  # Remaining

    def test_grid_coordinate_range(self, temp_images: list[Path]) -> None:
        """Test coordinate range property."""
        generator = GridGenerator(grid_size=5, thumbnail_size=50)
        grids = generator.generate_grids(temp_images)

        assert grids[0].coord_range == "A1-E5"

    def test_empty_images(self) -> None:
        """Test with empty image list."""
        generator = GridGenerator()
        grids = generator.generate_grids([])

        assert grids == []

    def test_grid_to_bytes(self, temp_images: list[Path]) -> None:
        """Test converting grid to JPEG bytes."""
        generator = GridGenerator(grid_size=5, thumbnail_size=50)
        grids = generator.generate_grids(temp_images)

        jpeg_bytes = generator.grid_to_bytes(grids[0])

        assert isinstance(jpeg_bytes, bytes)
        assert len(jpeg_bytes) > 0
        # JPEG magic bytes
        assert jpeg_bytes[:2] == b"\xff\xd8"


class TestCoordinateParsing:
    """Tests for parsing grid coordinates from model responses."""

    def test_parse_simple_list(self) -> None:
        """Test parsing a simple comma-separated list."""
        response = "A1, B3, C7, D12"
        matches = COORD_PATTERN.findall(response)

        coords = {f"{r.upper()}{c}" for r, c in matches}
        assert coords == {"A1", "B3", "C7", "D12"}

    def test_parse_with_text(self) -> None:
        """Test parsing coordinates embedded in text."""
        response = """Based on my analysis, I recommend selecting:
        - A1 (great composition)
        - B5 (dramatic lighting)
        - C10 (unique perspective)
        - T20 (memorable moment)
        """
        matches = COORD_PATTERN.findall(response)

        coords = {f"{r.upper()}{c}" for r, c in matches}
        assert coords == {"A1", "B5", "C10", "T20"}

    def test_parse_lowercase(self) -> None:
        """Test parsing lowercase coordinates."""
        response = "a1, b2, c3"
        matches = COORD_PATTERN.findall(response)

        coords = {f"{r.upper()}{c}" for r, c in matches}
        assert coords == {"A1", "B2", "C3"}

    def test_parse_no_spaces(self) -> None:
        """Test parsing without spaces."""
        response = "A1,B2,C3,D4"
        matches = COORD_PATTERN.findall(response)

        coords = {f"{r.upper()}{c}" for r, c in matches}
        assert coords == {"A1", "B2", "C3", "D4"}

    def test_invalid_coordinates_ignored(self) -> None:
        """Test that invalid coordinates are not matched."""
        response = "A1, Z99, AA1, B0, C21"
        matches = COORD_PATTERN.findall(response)

        # Z99 should not match (Z not in A-T)
        # AA1 should not match (two letters)
        # B0 should match (regex allows it, but validation would reject)
        # C21 should match (regex allows 1-2 digits)
        coords = {f"{r.upper()}{c}" for r, c in matches}
        assert "A1" in coords
        assert "Z99" not in coords  # Z is beyond T


class TestPrompts:
    """Tests for triage prompts."""

    def test_criteria_standout(self) -> None:
        """Test standout criteria description."""
        desc = get_criteria_description(CRITERIA_STANDOUT)
        assert "stand out" in desc.lower()
        assert "memorable" in desc.lower()

    def test_criteria_quality(self) -> None:
        """Test quality criteria description."""
        desc = get_criteria_description(CRITERIA_QUALITY)
        assert "quality" in desc.lower()
        assert "technical" in desc.lower()

    def test_custom_criteria(self) -> None:
        """Test custom criteria passthrough."""
        custom = "photos with dramatic sunsets"
        desc = get_criteria_description(custom)
        assert desc == custom

    def test_build_coarse_prompt(self) -> None:
        """Test building coarse triage prompt."""
        prompt = build_coarse_prompt(
            rows=20,
            cols=20,
            coord_range="A1-T20",
            total_photos=400,
            target_percentage=10.0,
            criteria="standout",
        )

        assert "400" in prompt
        assert "20" in prompt
        assert "A1-T20" in prompt
        assert "10" in prompt
        assert "40" in prompt  # target count
        assert "stand out" in prompt.lower()

    def test_build_fine_prompt(self) -> None:
        """Test building fine triage prompt."""
        prompt = build_fine_prompt(
            rows=4,
            cols=4,
            coord_range="A1-D4",
            total_photos=16,
            target_percentage=50.0,
            criteria="quality",
        )

        assert "16" in prompt
        assert "A1-D4" in prompt
        assert "50" in prompt
        assert "detailed" in prompt.lower()


class TestOutput:
    """Tests for output handling."""

    @pytest.fixture
    def source_images(self, tmp_path: Path) -> list[Path]:
        """Create source images in a temp directory."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        images = []
        for i in range(5):
            img_path = source_dir / f"photo_{i}.jpg"
            img = Image.new("RGB", (10, 10), color=(i, i, i))
            img.save(img_path, "JPEG")
            images.append(img_path)
        return images

    def test_create_selection_folder(
        self, tmp_path: Path, source_images: list[Path]
    ) -> None:
        """Test creating output folder with symlinks."""
        output_dir = tmp_path / "output"

        created = create_selection_folder(source_images, output_dir)

        assert created == 5
        assert output_dir.exists()

        # Check symlinks
        for img in source_images:
            link = output_dir / img.name
            assert link.exists()
            assert link.is_symlink()
            assert link.resolve() == img.resolve()

    def test_create_selection_folder_handles_collisions(self, tmp_path: Path) -> None:
        """Test handling of filename collisions."""
        # Create two images with same name in different directories
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        img1 = dir1 / "photo.jpg"
        img2 = dir2 / "photo.jpg"

        Image.new("RGB", (10, 10), color=(1, 1, 1)).save(img1, "JPEG")
        Image.new("RGB", (10, 10), color=(2, 2, 2)).save(img2, "JPEG")

        output_dir = tmp_path / "output"
        created = create_selection_folder([img1, img2], output_dir)

        assert created == 2

        # Both should exist (second with suffix)
        assert (output_dir / "photo.jpg").exists()
        assert (output_dir / "photo_1.jpg").exists()

    def test_create_selection_folder_overwrite(
        self, tmp_path: Path, source_images: list[Path]
    ) -> None:
        """Test overwriting existing output directory."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create an existing symlink
        old_link = output_dir / "old_link.jpg"
        old_link.symlink_to(source_images[0])

        created = create_selection_folder(source_images[:2], output_dir, overwrite=True)

        assert created == 2
        assert not old_link.exists()  # Old link should be removed

    def test_create_selection_folder_exists_error(
        self, tmp_path: Path, source_images: list[Path]
    ) -> None:
        """Test error when output exists without overwrite."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with pytest.raises(FileExistsError):
            create_selection_folder(source_images, output_dir, overwrite=False)


class TestTriageSelector:
    """Tests for the triage selector."""

    def test_parse_target_percentage(self) -> None:
        """Test parsing percentage target."""
        selector = TriageSelector.__new__(TriageSelector)
        selector._client = None

        assert selector._parse_target("10%", 100) == 10.0
        assert selector._parse_target("25%", 200) == 25.0

    def test_parse_target_count(self) -> None:
        """Test parsing absolute count target."""
        selector = TriageSelector.__new__(TriageSelector)
        selector._client = None

        assert selector._parse_target("50", 200) == 25.0
        assert selector._parse_target("100", 1000) == 10.0

    def test_trim_to_target(self) -> None:
        """Test trimming selection to target."""
        selector = TriageSelector.__new__(TriageSelector)
        selector._client = None

        paths = [Path(f"/img_{i}.jpg") for i in range(100)]

        # 10% of 1000 = 100 target, but we only have 100 paths
        result = selector._trim_to_target(paths, 10.0, 1000)
        assert len(result) == 100

        # 5% of 1000 = 50 target
        result = selector._trim_to_target(paths, 5.0, 1000)
        assert len(result) == 50


class TestRowLabels:
    """Tests for row label generation."""

    def test_row_labels_count(self) -> None:
        """Test that we have 20 row labels."""
        assert len(ROW_LABELS) == 20

    def test_row_labels_start(self) -> None:
        """Test row labels start with A."""
        assert ROW_LABELS[0] == "A"

    def test_row_labels_end(self) -> None:
        """Test row labels end with T."""
        assert ROW_LABELS[19] == "T"
