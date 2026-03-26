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

# Legacy migration identity: all pre-existing rows were produced by cloud
# inference, so we normalize them to the canonical cloud identity that the
# desktop sidecar filters on.  This prevents stranding rows after upgrade.
_LEGACY_MODEL_NAME = "anthropic/claude-3.5-sonnet"
_LEGACY_MODEL_VERSION = "cloud-v1"


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
                    image_id TEXT NOT NULL,
                    composition REAL NOT NULL,
                    subject_strength REAL NOT NULL,
                    visual_appeal REAL NOT NULL,
                    sharpness REAL NOT NULL,
                    exposure_balance REAL NOT NULL,
                    noise_level REAL NOT NULL,
                    model_name TEXT NOT NULL DEFAULT 'unknown',
                    model_version TEXT NOT NULL DEFAULT 'unknown',
                    scored_at TEXT,
                    synced_at TEXT,
                    PRIMARY KEY (image_id, model_name, model_version)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS image_metadata (
                    image_id TEXT NOT NULL,
                    model_name TEXT NOT NULL DEFAULT 'unknown',
                    date_taken TEXT,
                    latitude REAL,
                    longitude REAL,
                    description TEXT,
                    location_name TEXT,
                    location_country TEXT,
                    PRIMARY KEY (image_id, model_name)
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
        """Migrate old schemas to current version."""
        with sqlite3.connect(self.db_path) as conn:
            # --- Migrate normalized_attributes ---
            cursor = conn.execute("PRAGMA table_info(normalized_attributes)")
            columns = {row[1]: row for row in cursor.fetchall()}

            # Add scored_at/synced_at if missing (v1 migration)
            if "scored_at" not in columns:
                conn.execute(
                    "ALTER TABLE normalized_attributes ADD COLUMN scored_at TEXT"
                )
            if "synced_at" not in columns:
                conn.execute(
                    "ALTER TABLE normalized_attributes ADD COLUMN synced_at TEXT"
                )

            # Check if PK is single-column (old schema: image_id TEXT PRIMARY KEY)
            # pk column index (5th element) > 0 means it's part of the PK
            pk_columns = [name for name, row in columns.items() if row[5] > 0]
            if pk_columns == ["image_id"]:
                # Old single-column PK — migrate to composite PK.
                # Only normalize rows that lack a real model identity (NULL or
                # 'unknown') to the canonical cloud pair.  Rows that already
                # carry an explicit model_name (e.g. google/gemini-*) are
                # preserved as-is; overwriting them would be data corruption.
                conn.execute(
                    """UPDATE normalized_attributes
                       SET model_name = ?, model_version = ?
                       WHERE model_name IS NULL
                          OR model_name = ''
                          OR model_name = 'unknown'""",
                    (_LEGACY_MODEL_NAME, _LEGACY_MODEL_VERSION),
                )
                # Rows with an explicit model_name but NULL/unknown version
                # get the version backfilled so the NOT NULL constraint holds.
                conn.execute(
                    """UPDATE normalized_attributes
                       SET model_version = 'unknown'
                       WHERE model_version IS NULL""",
                )
                conn.execute("""
                    CREATE TABLE normalized_attributes_new (
                        image_id TEXT NOT NULL,
                        composition REAL NOT NULL,
                        subject_strength REAL NOT NULL,
                        visual_appeal REAL NOT NULL,
                        sharpness REAL NOT NULL,
                        exposure_balance REAL NOT NULL,
                        noise_level REAL NOT NULL,
                        model_name TEXT NOT NULL DEFAULT 'unknown',
                        model_version TEXT NOT NULL DEFAULT 'unknown',
                        scored_at TEXT,
                        synced_at TEXT,
                        PRIMARY KEY (image_id, model_name, model_version)
                    )
                """)
                conn.execute("""
                    INSERT INTO normalized_attributes_new
                    SELECT image_id, composition, subject_strength, visual_appeal,
                           sharpness, exposure_balance, noise_level,
                           model_name, model_version, scored_at, synced_at
                    FROM normalized_attributes
                """)
                conn.execute("DROP TABLE normalized_attributes")
                conn.execute(
                    "ALTER TABLE normalized_attributes_new RENAME TO normalized_attributes"
                )

            # --- Migrate image_metadata ---
            cursor = conn.execute("PRAGMA table_info(image_metadata)")
            meta_columns = {row[1]: row for row in cursor.fetchall()}

            if "model_name" not in meta_columns:
                # Old schema without model_name — add column and migrate to composite PK.
                # Normalize to the canonical cloud identity (same as attributes).
                conn.execute("""
                    CREATE TABLE image_metadata_new (
                        image_id TEXT NOT NULL,
                        model_name TEXT NOT NULL DEFAULT 'unknown',
                        date_taken TEXT,
                        latitude REAL,
                        longitude REAL,
                        description TEXT,
                        location_name TEXT,
                        location_country TEXT,
                        PRIMARY KEY (image_id, model_name)
                    )
                """)
                conn.execute(
                    """
                    INSERT INTO image_metadata_new
                    (image_id, model_name, date_taken, latitude, longitude,
                     description, location_name, location_country)
                    SELECT image_id, ?, date_taken, latitude, longitude,
                           description, location_name, location_country
                    FROM image_metadata
                """,
                    (_LEGACY_MODEL_NAME,),
                )
                conn.execute("DROP TABLE image_metadata")
                conn.execute("ALTER TABLE image_metadata_new RENAME TO image_metadata")
            else:
                # model_name column exists — check if PK needs migration
                meta_pk_columns = [
                    name for name, row in meta_columns.items() if row[5] > 0
                ]
                if meta_pk_columns == ["image_id"]:
                    # Single-column PK with model_name column — migrate to composite PK.
                    # Only normalize NULL/empty/unknown rows; preserve explicit identities.
                    conn.execute(
                        """UPDATE image_metadata SET model_name = ?
                           WHERE model_name IS NULL
                              OR model_name = ''
                              OR model_name = 'unknown'""",
                        (_LEGACY_MODEL_NAME,),
                    )
                    conn.execute("""
                        CREATE TABLE image_metadata_new (
                            image_id TEXT NOT NULL,
                            model_name TEXT NOT NULL DEFAULT 'unknown',
                            date_taken TEXT,
                            latitude REAL,
                            longitude REAL,
                            description TEXT,
                            location_name TEXT,
                            location_country TEXT,
                            PRIMARY KEY (image_id, model_name)
                        )
                    """)
                    conn.execute("""
                        INSERT INTO image_metadata_new
                        SELECT image_id, model_name, date_taken, latitude, longitude,
                               description, location_name, location_country
                        FROM image_metadata
                    """)
                    conn.execute("DROP TABLE image_metadata")
                    conn.execute(
                        "ALTER TABLE image_metadata_new RENAME TO image_metadata"
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

    def get_attributes(
        self,
        image_id: str,
        model_name: str | None = None,
        model_version: str | None = None,
    ) -> NormalizedAttributes | None:
        """Retrieve cached normalized attributes.

        Args:
            image_id: Image hash.
            model_name: If provided, filter to this model.
            model_version: If provided, filter to this version.

        When all three are provided, does exact PK lookup.
        When partial/none, returns most recent by scored_at.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if model_name is not None and model_version is not None:
                cursor = conn.execute(
                    "SELECT * FROM normalized_attributes WHERE image_id = ? AND model_name = ? AND model_version = ?",
                    (image_id, model_name, model_version),
                )
            elif model_name is not None:
                cursor = conn.execute(
                    "SELECT * FROM normalized_attributes WHERE image_id = ? AND model_name = ? ORDER BY scored_at DESC LIMIT 1",
                    (image_id, model_name),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM normalized_attributes WHERE image_id = ? ORDER BY scored_at DESC LIMIT 1",
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

        Uses INSERT ... ON CONFLICT on composite PK (image_id, model_name, model_version)
        to preserve synced_at on updates.
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
                ON CONFLICT(image_id, model_name, model_version) DO UPDATE SET
                    composition = excluded.composition,
                    subject_strength = excluded.subject_strength,
                    visual_appeal = excluded.visual_appeal,
                    sharpness = excluded.sharpness,
                    exposure_balance = excluded.exposure_balance,
                    noise_level = excluded.noise_level,
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

    def mark_synced(self, rows: list[tuple[str, str, str]] | list[str]) -> None:
        """Mark attributes as synced by setting synced_at to now (UTC).

        Args:
            rows: List of (image_id, model_name, model_version) tuples,
                  or list of image_ids for backward compatibility.
        """
        if not rows:
            return
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            # Detect whether caller passed tuples or plain strings
            if isinstance(rows[0], str):
                # Backward compat: mark all rows for these image_ids
                placeholders = ",".join("?" for _ in rows)
                conn.execute(
                    f"UPDATE normalized_attributes SET synced_at = ? WHERE image_id IN ({placeholders})",
                    [now, *rows],
                )
            else:
                # New API: mark specific (image_id, model_name, model_version) rows
                for image_id, model_name, model_version in rows:
                    conn.execute(
                        "UPDATE normalized_attributes SET synced_at = ? WHERE image_id = ? AND model_name = ? AND model_version = ?",
                        (now, image_id, model_name, model_version),
                    )
            conn.commit()

    def list_unsynced_attributes(
        self,
        model_name: str | None = None,
        model_version: str | None = None,
    ) -> list[NormalizedAttributes]:
        """Return attributes that have never been synced or changed since last sync.

        Args:
            model_name: If provided, only return rows matching this model.
            model_version: If provided, also filter by version.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM normalized_attributes WHERE (synced_at IS NULL OR scored_at > synced_at)"
            params: list = []

            if model_name is not None:
                query += " AND model_name = ?"
                params.append(model_name)
            if model_version is not None:
                query += " AND model_version = ?"
                params.append(model_version)

            cursor = conn.execute(query, params)
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

    def list_all_metadata_for(
        self,
        image_ids: list[str],
        model_name: str | None = None,
    ) -> dict[str, ImageMetadata]:
        """Batch lookup metadata by image_id list.

        Args:
            image_ids: List of image hashes to look up.
            model_name: If provided, return only metadata from this model.
                        If None, return one per image_id (latest by rowid).
        """
        if not image_ids:
            return {}
        result: dict[str, ImageMetadata] = {}
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            placeholders = ",".join("?" for _ in image_ids)

            if model_name is not None:
                cursor = conn.execute(
                    f"SELECT * FROM image_metadata WHERE image_id IN ({placeholders}) AND model_name = ?",
                    [*image_ids, model_name],
                )
            else:
                cursor = conn.execute(
                    f"SELECT * FROM image_metadata WHERE image_id IN ({placeholders})",
                    image_ids,
                )

            for row in cursor.fetchall():
                date_taken = None
                if row["date_taken"]:
                    date_taken = datetime.fromisoformat(row["date_taken"])
                # When no model filter, last row wins (one per image_id)
                result[row["image_id"]] = ImageMetadata(
                    date_taken=date_taken,
                    latitude=row["latitude"],
                    longitude=row["longitude"],
                    description=row["description"],
                    location_name=row["location_name"],
                    location_country=row["location_country"],
                )
        return result

    def has_attributes(
        self,
        image_id: str,
        model_name: str | None = None,
        model_version: str | None = None,
    ) -> bool:
        """Check if attributes exist for an image."""
        with sqlite3.connect(self.db_path) as conn:
            if model_name is not None and model_version is not None:
                cursor = conn.execute(
                    "SELECT 1 FROM normalized_attributes WHERE image_id = ? AND model_name = ? AND model_version = ?",
                    (image_id, model_name, model_version),
                )
            elif model_name is not None:
                cursor = conn.execute(
                    "SELECT 1 FROM normalized_attributes WHERE image_id = ? AND model_name = ?",
                    (image_id, model_name),
                )
            else:
                cursor = conn.execute(
                    "SELECT 1 FROM normalized_attributes WHERE image_id = ?",
                    (image_id,),
                )
            return cursor.fetchone() is not None

    def get_metadata(
        self,
        image_id: str,
        model_name: str | None = None,
    ) -> Optional[ImageMetadata]:
        """Retrieve cached image metadata.

        Args:
            image_id: Image hash.
            model_name: If provided, exact (image_id, model_name) lookup.
                        If None, returns latest by rowid (backward compat).
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if model_name is not None:
                cursor = conn.execute(
                    "SELECT * FROM image_metadata WHERE image_id = ? AND model_name = ?",
                    (image_id, model_name),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM image_metadata WHERE image_id = ? ORDER BY rowid DESC LIMIT 1",
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

    def store_metadata(
        self,
        image_id: str,
        metadata: ImageMetadata,
        model_name: str = "unknown",
    ) -> None:
        """Store image metadata in cache."""
        date_str = None
        if metadata.date_taken:
            date_str = metadata.date_taken.isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO image_metadata
                (image_id, model_name, date_taken, latitude, longitude, description, location_name, location_country)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    image_id,
                    model_name,
                    date_str,
                    metadata.latitude,
                    metadata.longitude,
                    metadata.description,
                    metadata.location_name,
                    metadata.location_country,
                ),
            )
            conn.commit()

    def has_metadata(
        self,
        image_id: str,
        model_name: str | None = None,
    ) -> bool:
        """Check if metadata exists for an image."""
        with sqlite3.connect(self.db_path) as conn:
            if model_name is not None:
                cursor = conn.execute(
                    "SELECT 1 FROM image_metadata WHERE image_id = ? AND model_name = ?",
                    (image_id, model_name),
                )
            else:
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
