#!/usr/bin/env python3
"""Script to deduplicate existing photos and backfill image_hash.

This script:
1. Downloads each photo from Supabase Storage
2. Computes SHA256 hash of the content
3. Updates the image_hash column
4. Identifies duplicates (same user + same hash)
5. Keeps the oldest photo (or the one with scores) and deletes duplicates

Usage:
    # Dry run (see what would be deleted)
    python dedupe_photos.py --dry-run

    # Actually delete duplicates
    python dedupe_photos.py

Requires environment variables:
    SUPABASE_URL
    SUPABASE_SERVICE_KEY
"""

import argparse
import hashlib
import os
from collections import defaultdict

from supabase import create_client

# Get Supabase credentials from environment
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")


def get_supabase():
    """Create Supabase client."""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def compute_image_hash(supabase, storage_path: str) -> str | None:
    """Download image and compute SHA256 hash."""
    try:
        data = supabase.storage.from_("photos").download(storage_path)
        if isinstance(data, bytes):
            return hashlib.sha256(data).hexdigest()
        return None
    except Exception as e:
        print(f"  Error downloading {storage_path}: {e}")
        return None


def backfill_hashes(supabase, dry_run: bool = True) -> dict[str, list[dict]]:
    """Backfill image_hash for all photos and return duplicates grouped by hash."""
    print("Fetching all photos...")

    # Get all photos without image_hash or all photos
    result = (
        supabase.table("scored_photos")
        .select("id, user_id, storage_path, image_hash, final_score, created_at")
        .order("created_at")
        .execute()
    )

    photos = result.data
    print(f"Found {len(photos)} total photos")

    # Group by user_id -> image_hash -> list of photos
    user_hashes: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))

    updated = 0
    for i, photo in enumerate(photos):
        print(f"\rProcessing {i + 1}/{len(photos)}...", end="", flush=True)

        # Compute hash if not already set
        if photo.get("image_hash"):
            image_hash = photo["image_hash"]
        else:
            image_hash = compute_image_hash(supabase, photo["storage_path"])

            if image_hash and not dry_run:
                # Update the photo with the hash
                supabase.table("scored_photos").update({"image_hash": image_hash}).eq(
                    "id", photo["id"]
                ).execute()
                updated += 1

        if image_hash:
            photo["image_hash"] = image_hash
            user_hashes[photo["user_id"]][image_hash].append(photo)

    print(f"\nBackfilled {updated} photos with image_hash")

    # Find duplicates (more than one photo with same user_id + image_hash)
    duplicates: dict[str, list[dict]] = {}
    for user_id, hashes in user_hashes.items():
        for image_hash, photos_list in hashes.items():
            if len(photos_list) > 1:
                key = f"{user_id}:{image_hash[:12]}"
                duplicates[key] = photos_list

    return duplicates


def choose_photo_to_keep(photos: list[dict]) -> dict:
    """Choose which photo to keep from a list of duplicates.

    Priority:
    1. Photo with a final_score (already scored)
    2. Oldest photo (by created_at)
    """
    # Prefer photos with scores
    scored = [p for p in photos if p.get("final_score") is not None]
    if scored:
        # Return the oldest scored photo
        return min(scored, key=lambda p: p["created_at"])

    # Otherwise return the oldest photo
    return min(photos, key=lambda p: p["created_at"])


def delete_duplicates(supabase, duplicates: dict[str, list[dict]], dry_run: bool = True):
    """Delete duplicate photos, keeping one per group."""
    total_to_delete = 0
    storage_to_delete = []
    ids_to_delete = []

    print(f"\nFound {len(duplicates)} groups of duplicates:")

    for key, photos in duplicates.items():
        keep = choose_photo_to_keep(photos)
        to_delete = [p for p in photos if p["id"] != keep["id"]]

        print(f"\n  Group {key}:")
        print(
            f"    Keeping: {keep['id']} (score: {keep.get('final_score')}, created: {keep['created_at']})"
        )
        for p in to_delete:
            print(
                f"    Deleting: {p['id']} (score: {p.get('final_score')}, created: {p['created_at']})"
            )
            ids_to_delete.append(p["id"])
            storage_to_delete.append(p["storage_path"])

        total_to_delete += len(to_delete)

    print(f"\nTotal photos to delete: {total_to_delete}")

    if dry_run:
        print("\n[DRY RUN] No changes made. Run without --dry-run to delete duplicates.")
        return

    # Delete from database
    if ids_to_delete:
        print(f"\nDeleting {len(ids_to_delete)} database records...")
        for photo_id in ids_to_delete:
            supabase.table("scored_photos").delete().eq("id", photo_id).execute()
        print("Database records deleted.")

    # Delete from storage
    if storage_to_delete:
        print(f"Deleting {len(storage_to_delete)} storage files...")
        # Supabase storage remove accepts a list
        try:
            supabase.storage.from_("photos").remove(storage_to_delete)
            print("Storage files deleted.")
        except Exception as e:
            print(f"Error deleting some storage files: {e}")
            # Try one by one
            for path in storage_to_delete:
                try:
                    supabase.storage.from_("photos").remove([path])
                except Exception:
                    print(f"  Could not delete: {path}")

    print("\nDeduplication complete!")


def main():
    parser = argparse.ArgumentParser(description="Deduplicate photos in the database")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without making changes",
    )
    args = parser.parse_args()

    supabase = get_supabase()

    print("=" * 60)
    print("Photo Deduplication Script")
    print("=" * 60)

    if args.dry_run:
        print("MODE: Dry run (no changes will be made)\n")
    else:
        print("MODE: Live run (duplicates will be deleted)\n")

    # Backfill hashes and find duplicates
    duplicates = backfill_hashes(supabase, dry_run=args.dry_run)

    if not duplicates:
        print("\nNo duplicates found!")
        return

    # Delete duplicates
    delete_duplicates(supabase, duplicates, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
