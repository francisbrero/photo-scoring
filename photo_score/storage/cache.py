"""SQLite cache for inference results and attributes."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from photo_score.storage.models import (
    NormalizedAttributes,
    RawInferenceResult,
    ImageMetadata,
)

DEFAULT_CACHE_DIR = Path.home() / ".photo_score"
DEFAULT_CACHE_DB = DEFAULT_CACHE_DIR / "cache.db"


class Cache:
    """SQLite-based cache for inference results and normalized attributes."""

    def __init__(self, db_path: Path | None = None):
        """Initialize cache.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.photo_score/cache.db
        """
        if db_path is None:
            db_path = DEFAULT_CACHE_DB

        self.db_path = db_path
        self._ensure_dir()
        self._init_schema()
        self._migrate_schema()

    def _ensure_dir(self) -> None:
        """Ensure cache directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _init_schema(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inference_results (
                    image_id TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    raw_response TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (image_id, model_name, model_version)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS normalized_attributes (
                    image_id TEXT PRIMARY KEY,
                    composition REAL NOT NULL,
                    subject_strength REAL NOT NULL,
                    visual_appeal REAL NOT NULL,
                    sharpness REAL NOT NULL,
                    exposure_balance REAL NOT NULL,
                    noise_level REAL NOT NULL,
                    model_name TEXT,
                    model_version TEXT,
                    scored_at TEXT,
                    synced_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS image_metadata (
                    image_id TEXT PRIMARY KEY,
                    date_taken TEXT,
                    latitude REAL,
                    longitude REAL,
                    description TEXT,
                    location_name TEXT,
                    location_country TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS image_critique (
                    image_id TEXT PRIMARY KEY,
                    description TEXT,
                    explanation TEXT,
                    improvements TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def _migrate_schema(self) -> None:
        """Add new columns to existing databases."""
        with sqlite3.connect(self.db_path) as conn:
            # Get existing columns
            cursor = conn.execute("PRAGMA table_info(normalized_attributes)")
            existing = {row[1] for row in cursor.fetchall()}

            if "scored_at" not in existing:
                conn.execute(
                    "ALTER TABLE normalized_attributes ADD COLUMN scored_at TEXT"
                )
            if "synced_at" not in existing:
                conn.execute(
                    "ALTER TABLE normalized_attributes ADD COLUMN synced_at TEXT"
                )
            conn.commit()

    def get_inference(
        self, image_id: str, model_name: str, model_version: str
    ) -> RawInferenceResult | None:
        """Retrieve cached inference result."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM inference_results
                WHERE image_id = ? AND model_name = ? AND model_version = ?
                """,
                (image_id, model_name, model_version),
            )
            row = cursor.fetchone()
            if row is None:
                return None

            return RawInferenceResult(
                image_id=row["image_id"],
                model_name=row["model_name"],
                model_version=row["model_version"],
                raw_response=json.loads(row["raw_response"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )

    def store_inference(
        self,
        image_id: str,
        model_name: str,
        model_version: str,
        raw_response: dict,
    ) -> None:
        """Store inference result in cache."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO inference_results
                (image_id, model_name, model_version, raw_response, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    image_id,
                    model_name,
                    model_version,
                    json.dumps(raw_response),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

    def get_attributes(self, image_id: str) -> NormalizedAttributes | None:
        """Retrieve cached normalized attributes."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM normalized_attributes WHERE image_id = ?",
                (image_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None

            scored_at = None
            if row["scored_at"]:
                scored_at = datetime.fromisoformat(row["scored_at"])

            return NormalizedAttributes(
                image_id=row["image_id"],
                composition=row["composition"],
                subject_strength=row["subject_strength"],
                visual_appeal=row["visual_appeal"],
                sharpness=row["sharpness"],
                exposure_balance=row["exposure_balance"],
                noise_level=row["noise_level"],
                model_name=row["model_name"],
                model_version=row["model_version"],
                scored_at=scored_at,
            )

    def store_attributes(self, attributes: NormalizedAttributes) -> None:
        """Store normalized attributes in cache.

        Uses INSERT ... ON CONFLICT to preserve synced_at on updates.
        """
        scored_at_str = None
        if attributes.scored_at is not None:
            scored_at_str = attributes.scored_at.isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO normalized_attributes
                (image_id, composition, subject_strength, visual_appeal,
                 sharpness, exposure_balance, noise_level, model_name, model_version,
                 scored_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(image_id) DO UPDATE SET
                    composition = excluded.composition,
                    subject_strength = excluded.subject_strength,
                    visual_appeal = excluded.visual_appeal,
                    sharpness = excluded.sharpness,
                    exposure_balance = excluded.exposure_balance,
                    noise_level = excluded.noise_level,
                    model_name = excluded.model_name,
                    model_version = excluded.model_version,
                    scored_at = excluded.scored_at
                """,
                (
                    attributes.image_id,
                    attributes.composition,
                    attributes.subject_strength,
                    attributes.visual_appeal,
                    attributes.sharpness,
                    attributes.exposure_balance,
                    attributes.noise_level,
                    attributes.model_name,
                    attributes.model_version,
                    scored_at_str,
                ),
            )
            conn.commit()

    def mark_synced(self, image_ids: list[str]) -> None:
        """Mark attributes as synced by setting synced_at to now (UTC)."""
        if not image_ids:
            return
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            placeholders = ",".join("?" for _ in image_ids)
            conn.execute(
                f"UPDATE normalized_attributes SET synced_at = ? WHERE image_id IN ({placeholders})",
                [now, *image_ids],
            )
            conn.commit()

    def list_unsynced_attributes(self) -> list[NormalizedAttributes]:
        """Return attributes that have never been synced or changed since last sync."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM normalized_attributes
                WHERE synced_at IS NULL OR scored_at > synced_at
                """
            )
            results = []
            for row in cursor.fetchall():
                scored_at = None
                if row["scored_at"]:
                    scored_at = datetime.fromisoformat(row["scored_at"])
                results.append(
                    NormalizedAttributes(
                        image_id=row["image_id"],
                        composition=row["composition"],
                        subject_strength=row["subject_strength"],
                        visual_appeal=row["visual_appeal"],
                        sharpness=row["sharpness"],
                        exposure_balance=row["exposure_balance"],
                        noise_level=row["noise_level"],
                        model_name=row["model_name"],
                        model_version=row["model_version"],
                        scored_at=scored_at,
                    )
                )
            return results

    def list_all_metadata_for(self, image_ids: list[str]) -> dict[str, ImageMetadata]:
        """Batch lookup metadata by image_id list."""
        if not image_ids:
            return {}
        result: dict[str, ImageMetadata] = {}
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            placeholders = ",".join("?" for _ in image_ids)
            cursor = conn.execute(
                f"SELECT * FROM image_metadata WHERE image_id IN ({placeholders})",
                image_ids,
            )
            for row in cursor.fetchall():
                date_taken = None
                if row["date_taken"]:
                    date_taken = datetime.fromisoformat(row["date_taken"])
                result[row["image_id"]] = ImageMetadata(
                    date_taken=date_taken,
                    latitude=row["latitude"],
                    longitude=row["longitude"],
                    description=row["description"],
                    location_name=row["location_name"],
                    location_country=row["location_country"],
                )
        return result

    def has_attributes(self, image_id: str) -> bool:
        """Check if attributes exist for an image."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM normalized_attributes WHERE image_id = ?",
                (image_id,),
            )
            return cursor.fetchone() is not None

    def get_metadata(self, image_id: str) -> Optional[ImageMetadata]:
        """Retrieve cached image metadata."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM image_metadata WHERE image_id = ?",
                (image_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None

            date_taken = None
            if row["date_taken"]:
                date_taken = datetime.fromisoformat(row["date_taken"])

            return ImageMetadata(
                date_taken=date_taken,
                latitude=row["latitude"],
                longitude=row["longitude"],
                description=row["description"],
                location_name=row["location_name"],
                location_country=row["location_country"],
            )

    def store_metadata(self, image_id: str, metadata: ImageMetadata) -> None:
        """Store image metadata in cache."""
        date_str = None
        if metadata.date_taken:
            date_str = metadata.date_taken.isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO image_metadata
                (image_id, date_taken, latitude, longitude, description, location_name, location_country)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    image_id,
                    date_str,
                    metadata.latitude,
                    metadata.longitude,
                    metadata.description,
                    metadata.location_name,
                    metadata.location_country,
                ),
            )
            conn.commit()

    def has_metadata(self, image_id: str) -> bool:
        """Check if metadata exists for an image."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM image_metadata WHERE image_id = ?",
                (image_id,),
            )
            return cursor.fetchone() is not None

    def get_critique(self, image_id: str) -> Optional[dict]:
        """Retrieve cached critique data."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM image_critique WHERE image_id = ?",
                (image_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None

            improvements = []
            if row["improvements"]:
                improvements = json.loads(row["improvements"])

            return {
                "description": row["description"] or "",
                "explanation": row["explanation"] or "",
                "improvements": improvements,
            }

    def store_critique(
        self,
        image_id: str,
        description: str,
        explanation: str,
        improvements: list[str],
    ) -> None:
        """Store critique data in cache."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO image_critique
                (image_id, description, explanation, improvements, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    image_id,
                    description,
                    explanation,
                    json.dumps(improvements),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

    def has_critique(self, image_id: str) -> bool:
        """Check if critique exists for an image."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM image_critique WHERE image_id = ?",
                (image_id,),
            )
            return cursor.fetchone() is not None
