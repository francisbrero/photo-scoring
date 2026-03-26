"""Cloud sync handlers."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from photo_score.storage.cache import Cache
from photo_score.storage.models import ImageMetadata, NormalizedAttributes

from . import cloud_client

router = APIRouter()
logger = logging.getLogger(__name__)

PUSH_BATCH_SIZE = 500

# Sync-eligible model identity — must match the cloud API (packages/api)
SYNC_MODEL_NAME = "anthropic/claude-3.5-sonnet"
SYNC_MODEL_VERSION = "cloud-v1"

# Settings file for persisting sync cursor
SETTINGS_DIR = Path.home() / ".photo_score"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


class SyncRequest(BaseModel):
    """Request to sync with cloud."""

    auth_token: str
    cloud_url: Optional[str] = None


class SyncResponse(BaseModel):
    """Response from sync operation."""

    status: str
    synced: int
    errors: list[str]


class SyncStatusResponse(BaseModel):
    """Current sync status."""

    is_syncing: bool
    last_sync: Optional[str]
    pending_count: int


# Global sync state
_sync_state = {
    "is_syncing": False,
    "last_sync": None,
    "pending_count": 0,
}


def _load_settings() -> dict:
    """Load settings from file."""
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_settings(settings: dict) -> None:
    """Save settings to file."""
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status():
    """Get current sync status."""
    cache = Cache()
    unsynced = cache.list_unsynced_attributes(
        model_name=SYNC_MODEL_NAME, model_version=SYNC_MODEL_VERSION
    )
    return SyncStatusResponse(
        is_syncing=_sync_state["is_syncing"],
        last_sync=_sync_state["last_sync"],
        pending_count=len(unsynced),
    )


@router.post("/start", response_model=SyncResponse)
async def start_sync(request: SyncRequest):
    """Start syncing cached attributes to cloud."""
    global _sync_state

    if _sync_state["is_syncing"]:
        raise HTTPException(status_code=409, detail="Sync already in progress")

    _sync_state["is_syncing"] = True

    total_synced = 0
    errors: list[str] = []

    try:
        cache = Cache()
        settings = _load_settings()

        # Load pull cursor from settings
        cursor_since = settings.get("sync_cursor_since")
        cursor_after_id = settings.get("sync_cursor_after_id")

        # --- PUSH PHASE ---
        # Only sync desktop cloud rows (not local or CLI cloud rows)
        unsynced = cache.list_unsynced_attributes(
            model_name=SYNC_MODEL_NAME, model_version=SYNC_MODEL_VERSION
        )
        if unsynced:
            image_ids = [a.image_id for a in unsynced]
            metadata_map = cache.list_all_metadata_for(
                image_ids, model_name=SYNC_MODEL_NAME
            )

            # Batch into groups of PUSH_BATCH_SIZE
            for i in range(0, len(unsynced), PUSH_BATCH_SIZE):
                batch = unsynced[i : i + PUSH_BATCH_SIZE]
                records = []
                for attr in batch:
                    md = metadata_map.get(attr.image_id)
                    record: dict = {
                        "image_id": attr.image_id,
                        "attributes": {
                            "image_id": attr.image_id,
                            "composition": attr.composition,
                            "subject_strength": attr.subject_strength,
                            "visual_appeal": attr.visual_appeal,
                            "sharpness": attr.sharpness,
                            "exposure_balance": attr.exposure_balance,
                            "noise_level": attr.noise_level,
                            "model_name": attr.model_name,
                            "model_version": attr.model_version,
                        },
                        "scored_at": attr.scored_at.isoformat()
                        if attr.scored_at
                        else None,
                    }
                    if md:
                        record["metadata"] = md.model_dump(
                            mode="json", exclude_none=True
                        )
                    records.append(record)

                try:
                    result = await cloud_client.push_attributes(records)

                    # Mark successfully synced
                    synced_count = result.get("synced", 0)
                    total_synced += synced_count

                    # Mark synced ids (those not in conflicts)
                    conflict_ids = {c["image_id"] for c in result.get("conflicts", [])}
                    synced_rows = [
                        (r["image_id"], SYNC_MODEL_NAME, SYNC_MODEL_VERSION)
                        for r in records
                        if r["image_id"] not in conflict_ids
                    ]
                    if synced_rows:
                        cache.mark_synced(synced_rows)

                    # Handle conflicts: overwrite local with cloud version
                    for conflict in result.get("conflicts", []):
                        cid = conflict["image_id"]
                        cloud_rec = conflict.get("cloud_record", {})
                        cloud_attrs = cloud_rec.get("attributes", {})
                        if cloud_attrs:
                            scored_at = None
                            if cloud_rec.get("scored_at"):
                                try:
                                    scored_at = datetime.fromisoformat(
                                        cloud_rec["scored_at"]
                                    )
                                except (ValueError, TypeError):
                                    pass
                            attrs = NormalizedAttributes(
                                image_id=cid,
                                composition=cloud_attrs.get("composition", 0),
                                subject_strength=cloud_attrs.get("subject_strength", 0),
                                visual_appeal=cloud_attrs.get("visual_appeal", 0),
                                sharpness=cloud_attrs.get("sharpness", 0),
                                exposure_balance=cloud_attrs.get("exposure_balance", 0),
                                noise_level=cloud_attrs.get("noise_level", 0),
                                model_name=cloud_attrs.get(
                                    "model_name", SYNC_MODEL_NAME
                                ),
                                model_version=cloud_attrs.get(
                                    "model_version", SYNC_MODEL_VERSION
                                ),
                                scored_at=scored_at,
                            )
                            cache.store_attributes(attrs)

                        cloud_meta = cloud_rec.get("metadata")
                        if cloud_meta:
                            cache.store_metadata(
                                cid,
                                ImageMetadata(**cloud_meta),
                                model_name=cloud_attrs.get(
                                    "model_name", SYNC_MODEL_NAME
                                ),
                            )

                        cache.mark_synced(
                            [
                                (
                                    cid,
                                    cloud_attrs.get("model_name", SYNC_MODEL_NAME),
                                    cloud_attrs.get(
                                        "model_version", SYNC_MODEL_VERSION
                                    ),
                                )
                            ]
                        )

                except Exception as e:
                    logger.error(f"Push batch failed: {e}")
                    errors.append(f"Push error: {str(e)}")

        # --- PULL PHASE ---
        while True:
            try:
                result = await cloud_client.pull_attributes(
                    since=cursor_since, after_id=cursor_after_id
                )
            except Exception as e:
                logger.error(f"Pull failed: {e}")
                errors.append(f"Pull error: {str(e)}")
                break

            records = result.get("attributes", [])
            if not records:
                break

            for record in records:
                rid = record["image_id"]
                rattrs = record.get("attributes", {})
                r_model_name = rattrs.get("model_name", SYNC_MODEL_NAME)
                r_model_version = rattrs.get("model_version", SYNC_MODEL_VERSION)
                cloud_scored_at = None
                if record.get("scored_at"):
                    try:
                        cloud_scored_at = datetime.fromisoformat(record["scored_at"])
                    except (ValueError, TypeError):
                        pass

                # Only overwrite local if cloud is newer (or no local)
                local = cache.get_attributes(
                    rid, model_name=r_model_name, model_version=r_model_version
                )
                if local is not None and local.scored_at is not None:
                    if cloud_scored_at is None or cloud_scored_at <= local.scored_at:
                        continue

                attrs = NormalizedAttributes(
                    image_id=rid,
                    composition=rattrs.get("composition", 0),
                    subject_strength=rattrs.get("subject_strength", 0),
                    visual_appeal=rattrs.get("visual_appeal", 0),
                    sharpness=rattrs.get("sharpness", 0),
                    exposure_balance=rattrs.get("exposure_balance", 0),
                    noise_level=rattrs.get("noise_level", 0),
                    model_name=r_model_name,
                    model_version=r_model_version,
                    scored_at=cloud_scored_at,
                )
                cache.store_attributes(attrs)
                cache.mark_synced([(rid, r_model_name, r_model_version)])

                rmeta = record.get("metadata")
                if rmeta:
                    cache.store_metadata(
                        rid, ImageMetadata(**rmeta), model_name=r_model_name
                    )

            # Advance cursor from response (always present when
            # records are returned)
            next_cursor = result.get("next_cursor")
            if next_cursor:
                cursor_since = next_cursor["since"]
                cursor_after_id = next_cursor["after_id"]

            # Stop when we got a partial page (fewer than default limit)
            # — that means we've consumed everything
            if len(records) < 500:
                break

        # Persist cursor to settings
        settings["sync_cursor_since"] = cursor_since
        settings["sync_cursor_after_id"] = cursor_after_id
        _save_settings(settings)

        _sync_state["last_sync"] = datetime.now(timezone.utc).isoformat()
        _sync_state["pending_count"] = len(
            cache.list_unsynced_attributes(
                model_name=SYNC_MODEL_NAME, model_version=SYNC_MODEL_VERSION
            )
        )

        return SyncResponse(
            status="completed" if not errors else "partial",
            synced=total_synced,
            errors=errors,
        )
    except Exception as e:
        logger.exception("Sync failed")
        return SyncResponse(
            status="failed",
            synced=total_synced,
            errors=[*errors, str(e)],
        )
    finally:
        _sync_state["is_syncing"] = False


@router.post("/stop")
async def stop_sync():
    """Stop ongoing sync."""
    global _sync_state

    if not _sync_state["is_syncing"]:
        return {"status": "not_syncing"}

    _sync_state["is_syncing"] = False
    return {"status": "stopped"}
