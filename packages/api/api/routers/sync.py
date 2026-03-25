"""Sync router for bi-directional attribute sync between desktop and cloud."""

from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from ..dependencies import CurrentUser, SupabaseClient

router = APIRouter()

MAX_BATCH_SIZE = 1000
DEFAULT_PULL_LIMIT = 500
MAX_PULL_LIMIT = 2000


# --- Request / Response Models ---


class AttributeRecord(BaseModel):
    """A single attribute record for push."""

    image_id: str
    attributes: dict[str, float]
    metadata: dict | None = None
    scored_at: str | None = None


class PushRequest(BaseModel):
    """Push batch of attribute records."""

    attributes: list[AttributeRecord] = Field(..., min_length=1, max_length=MAX_BATCH_SIZE)


class ConflictRecord(BaseModel):
    """A conflict returned from push."""

    image_id: str
    reason: str
    cloud_record: dict


class PushResponse(BaseModel):
    """Response from push."""

    synced: int
    conflicts: list[ConflictRecord]


class PullRecord(BaseModel):
    """A single record in pull response."""

    image_id: str
    attributes: dict[str, float]
    metadata: dict | None = None
    scored_at: str | None = None


class PullCursor(BaseModel):
    """Cursor for paginated pull."""

    since: str
    after_id: str


class PullResponse(BaseModel):
    """Response from pull."""

    attributes: list[PullRecord]
    next_cursor: PullCursor | None = None


class SyncStatusResponse(BaseModel):
    """Response from sync status."""

    last_sync: str | None
    cloud_count: int


# --- Helpers ---


def _parse_scored_at(value: str | None) -> datetime | None:
    """Parse a scored_at string to datetime, returning None on failure."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _is_newer(incoming: str | None, existing: str | None) -> bool:
    """Return True if incoming scored_at is strictly newer than existing.

    None = oldest (always loses to non-None).
    """
    incoming_dt = _parse_scored_at(incoming)
    existing_dt = _parse_scored_at(existing)

    if incoming_dt is None:
        return False
    if existing_dt is None:
        return True
    return incoming_dt > existing_dt


# --- Endpoints ---


@router.post("/attributes", response_model=PushResponse)
async def push_attributes(
    request: PushRequest,
    user: CurrentUser,
    supabase: SupabaseClient,
):
    """Push a batch of attribute records to the cloud.

    For each record:
    - If no existing cloud record: insert
    - If existing and incoming scored_at is strictly newer: update
    - Otherwise: conflict (cloud wins), returns cloud_record so client can reconcile
    """
    synced = 0
    conflicts: list[ConflictRecord] = []

    for record in request.attributes:
        image_hash = record.image_id

        # Look up existing
        existing_result = (
            supabase.table("inference_cache")
            .select("id, attributes, scored_at")
            .eq("user_id", user.id)
            .eq("image_hash", image_hash)
            .execute()
        )

        if not existing_result.data:
            # No existing — insert
            insert_data: dict = {
                "user_id": user.id,
                "image_hash": image_hash,
                "attributes": record.attributes,
            }
            if record.scored_at:
                insert_data["scored_at"] = record.scored_at
            supabase.table("inference_cache").insert(insert_data).execute()

            # Upsert metadata if provided
            if record.metadata:
                _upsert_metadata(supabase, user.id, image_hash, record.metadata)

            synced += 1
        else:
            existing = existing_result.data[0]
            existing_scored_at = existing.get("scored_at")

            if _is_newer(record.scored_at, existing_scored_at):
                # Incoming is newer — update
                update_data: dict = {"attributes": record.attributes}
                if record.scored_at:
                    update_data["scored_at"] = record.scored_at
                (
                    supabase.table("inference_cache")
                    .update(update_data)
                    .eq("user_id", user.id)
                    .eq("image_hash", image_hash)
                    .execute()
                )

                if record.metadata:
                    _upsert_metadata(supabase, user.id, image_hash, record.metadata)

                synced += 1
            else:
                # Cloud wins — build cloud_record for client
                cloud_record: dict = {
                    "attributes": existing["attributes"],
                    "scored_at": existing_scored_at,
                }
                # Fetch metadata for the cloud record
                meta_result = (
                    supabase.table("metadata_cache")
                    .select("metadata")
                    .eq("user_id", user.id)
                    .eq("image_hash", image_hash)
                    .execute()
                )
                if meta_result.data:
                    cloud_record["metadata"] = meta_result.data[0]["metadata"]

                conflicts.append(
                    ConflictRecord(
                        image_id=record.image_id,
                        reason="cloud_newer_or_equal",
                        cloud_record=cloud_record,
                    )
                )

    return PushResponse(synced=synced, conflicts=conflicts)


@router.get("/attributes", response_model=PullResponse)
async def pull_attributes(
    user: CurrentUser,
    supabase: SupabaseClient,
    since: str | None = Query(None, description="Cursor: updated_at timestamp"),
    after_id: str | None = Query(None, description="Cursor: record id"),
    limit: int = Query(DEFAULT_PULL_LIMIT, ge=1, le=MAX_PULL_LIMIT),
):
    """Pull attribute records from the cloud with cursor-based pagination.

    Cursor is (updated_at, id) for stable ordering.
    """
    query = (
        supabase.table("inference_cache")
        .select("id, image_hash, attributes, scored_at, updated_at")
        .eq("user_id", user.id)
        .order("updated_at", desc=False)
        .order("id", desc=False)
        .limit(limit)
    )

    if since and after_id:
        # Cursor pagination: (updated_at > since) OR (updated_at = since AND id > after_id)
        query = query.or_(f"updated_at.gt.{since},and(updated_at.eq.{since},id.gt.{after_id})")
    elif since:
        query = query.gt("updated_at", since)

    result = query.execute()
    rows = result.data or []

    # Batch-fetch metadata for returned image hashes
    image_hashes = [row["image_hash"] for row in rows]
    metadata_map: dict[str, dict] = {}
    if image_hashes:
        meta_result = (
            supabase.table("metadata_cache")
            .select("image_hash, metadata")
            .eq("user_id", user.id)
            .in_("image_hash", image_hashes)
            .execute()
        )
        for meta_row in meta_result.data or []:
            metadata_map[meta_row["image_hash"]] = meta_row["metadata"]

    # Build response
    records: list[PullRecord] = []
    for row in rows:
        meta = metadata_map.get(row["image_hash"])
        scored_at_val = row.get("scored_at")
        records.append(
            PullRecord(
                image_id=row["image_hash"],
                attributes=row["attributes"],
                metadata=meta,
                scored_at=scored_at_val,
            )
        )

    # Build next cursor
    next_cursor = None
    if rows and len(rows) == limit:
        last = rows[-1]
        next_cursor = PullCursor(
            since=last["updated_at"],
            after_id=last["id"],
        )

    return PullResponse(attributes=records, next_cursor=next_cursor)


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    user: CurrentUser,
    supabase: SupabaseClient,
):
    """Get sync status: cloud record count and last sync time."""
    # Count records
    count_result = (
        supabase.table("inference_cache")
        .select("id", count="exact")
        .eq("user_id", user.id)
        .execute()
    )
    cloud_count = count_result.count or 0

    # Get most recent updated_at as proxy for last sync
    latest_result = (
        supabase.table("inference_cache")
        .select("updated_at")
        .eq("user_id", user.id)
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )
    last_sync = None
    if latest_result.data:
        last_sync = latest_result.data[0]["updated_at"]

    return SyncStatusResponse(last_sync=last_sync, cloud_count=cloud_count)


def _upsert_metadata(supabase, user_id: str, image_hash: str, metadata: dict) -> None:
    """Upsert metadata_cache record."""
    existing = (
        supabase.table("metadata_cache")
        .select("id")
        .eq("user_id", user_id)
        .eq("image_hash", image_hash)
        .execute()
    )
    if existing.data:
        (
            supabase.table("metadata_cache")
            .update({"metadata": metadata})
            .eq("user_id", user_id)
            .eq("image_hash", image_hash)
            .execute()
        )
    else:
        supabase.table("metadata_cache").insert(
            {
                "user_id": user_id,
                "image_hash": image_hash,
                "metadata": metadata,
            }
        ).execute()
