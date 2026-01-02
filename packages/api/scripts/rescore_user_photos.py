#!/usr/bin/env python3
"""Rescore all photos for specific users.

This script re-runs the scoring pipeline for all photos belonging to
specified users. Useful when scoring logic changes and you need to
update existing photos.

Usage:
    # Rescore for specific users (dry run by default)
    python scripts/rescore_user_photos.py USER_ID1 USER_ID2

    # Actually perform the rescore
    python scripts/rescore_user_photos.py USER_ID1 --execute

    # Use production Supabase
    python scripts/rescore_user_photos.py USER_ID1 --production --execute

Environment variables (loaded from .env automatically):
    SUPABASE_URL: Supabase project URL
    SUPABASE_SERVICE_KEY: Service role key (for admin access)
    OPENROUTER_API_KEY: OpenRouter API key for AI inference
"""

import argparse
import asyncio
import hashlib
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env files - root project .env first (for production credentials),
# then local .env files (which may override for local development)
try:
    from dotenv import load_dotenv

    # Root project .env (contains production credentials)
    root_env = Path(__file__).parent.parent.parent.parent / ".env"
    if root_env.exists():
        load_dotenv(root_env)

    # Local .env files (may override for local dev)
    local_env = Path(__file__).parent.parent / ".env"
    local_env_local = Path(__file__).parent.parent / ".env.local"
    if local_env.exists():
        load_dotenv(local_env, override=True)
    if local_env_local.exists():
        load_dotenv(local_env_local, override=True)
except ImportError:
    pass  # dotenv not installed, rely on system env vars


def get_supabase_client(production: bool = False):
    """Create Supabase client."""
    from supabase import create_client

    if production:
        # For production, load only from root .env (not local overrides)
        from dotenv import dotenv_values

        root_env = Path(__file__).parent.parent.parent.parent / ".env"
        if not root_env.exists():
            print(f"ERROR: Root .env file not found at {root_env}")
            sys.exit(1)

        config = dotenv_values(root_env)
        url = config.get("SUPABASE_URL")
        key = config.get("SUPABASE_SERVICE_KEY")

        if not url or not key:
            print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in root .env")
            print(f"Root .env path: {root_env}")
            sys.exit(1)

        print(f"Using production Supabase: {url[:50]}...")
    else:
        # Local Supabase defaults
        url = "http://127.0.0.1:54321"
        key = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0."
            "EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"
        )

    return create_client(url, key)


async def rescore_photo(supabase, photo: dict, inference_service) -> dict:
    """Rescore a single photo."""
    photo_id = photo["id"]
    user_id = photo["user_id"]
    storage_path = photo["storage_path"]

    # Download image from storage
    try:
        download_result = supabase.storage.from_("photos").download(storage_path)
        if isinstance(download_result, bytes):
            image_data = download_result
        elif hasattr(download_result, "read"):
            image_data = download_result.read()
        else:
            image_data = bytes(download_result)
    except Exception as e:
        return {"error": f"Failed to download image: {e}"}

    # Compute image hash
    image_hash = hashlib.sha256(image_data).hexdigest()

    # Run inference (attributes)
    try:
        attributes = await inference_service.analyze_image(image_data, image_hash)
    except Exception as e:
        return {"error": f"Failed to analyze image: {e}"}

    # Extract features
    try:
        features = await inference_service.extract_features(image_data)
    except Exception:
        features = {
            "scene_type": "other",
            "main_subject": "unclear",
            "subject_position": "center",
            "background": "unknown",
            "lighting": "unknown",
            "color_palette": "neutral",
            "depth_of_field": "medium",
            "time_of_day": "unknown",
        }

    # Compute scores
    scores = inference_service.compute_scores(attributes)

    # Generate rich critique
    try:
        critique = await inference_service.generate_critique(
            image_data, features, attributes, scores["final_score"]
        )
        explanation = inference_service.format_explanation(critique)
        improvements = inference_service.format_improvements(critique)
    except Exception as e:
        explanation = f"Failed to generate critique: {e}"
        improvements = "No improvements available."

    # Get metadata
    try:
        metadata = await inference_service.analyze_image_metadata(image_data, image_hash)
        description = metadata.get("description")
        location_name = metadata.get("location_name")
        location_country = metadata.get("location_country")
    except Exception:
        description = None
        location_name = None
        location_country = None

    # Update photo in database
    update_data = {
        "final_score": scores["final_score"],
        "aesthetic_score": scores["aesthetic_score"],
        "technical_score": scores["technical_score"],
        "description": description,
        "explanation": explanation,
        "improvements": improvements,
        "location_name": location_name,
        "location_country": location_country,
        "model_scores": {
            "composition": attributes.get("composition"),
            "subject_strength": attributes.get("subject_strength"),
            "visual_appeal": attributes.get("visual_appeal"),
            "sharpness": attributes.get("sharpness"),
            "exposure_balance": attributes.get("exposure_balance"),
            "noise_level": attributes.get("noise_level"),
        },
        "features_json": features,
        "updated_at": datetime.now(UTC).isoformat(),
    }

    supabase.table("scored_photos").update(update_data).eq("id", photo_id).execute()

    # Update caches
    try:
        # Inference cache
        supabase.table("inference_cache").upsert(
            {
                "user_id": user_id,
                "image_hash": image_hash,
                "attributes": attributes,
            }
        ).execute()

        # Features cache
        supabase.table("features_cache").upsert(
            {
                "user_id": user_id,
                "image_hash": image_hash,
                "features": features,
            }
        ).execute()

        # Metadata cache
        if description:
            supabase.table("metadata_cache").upsert(
                {
                    "user_id": user_id,
                    "image_hash": image_hash,
                    "metadata": {
                        "description": description,
                        "location_name": location_name,
                        "location_country": location_country,
                    },
                }
            ).execute()
    except Exception:
        pass  # Cache updates are optional

    return {
        "photo_id": photo_id,
        "final_score": scores["final_score"],
        "aesthetic_score": scores["aesthetic_score"],
        "technical_score": scores["technical_score"],
    }


async def rescore_user_photos(
    supabase, user_id: str, inference_service, dry_run: bool = True
) -> list[dict]:
    """Rescore all photos for a user."""
    # Get all photos for user
    result = (
        supabase.table("scored_photos")
        .select("id, user_id, storage_path, final_score")
        .eq("user_id", user_id)
        .execute()
    )

    photos = result.data
    if not photos:
        print(f"  No photos found for user {user_id}")
        return []

    print(f"  Found {len(photos)} photos for user {user_id}")

    if dry_run:
        print("  [DRY RUN] Would rescore:")
        for photo in photos:
            print(f"    - {photo['id']} (current score: {photo.get('final_score', 'N/A')})")
        return []

    results = []
    for i, photo in enumerate(photos, 1):
        print(f"  [{i}/{len(photos)}] Rescoring {photo['id']}...", end=" ", flush=True)
        try:
            result = await rescore_photo(supabase, photo, inference_service)
            if "error" in result:
                print(f"ERROR: {result['error']}")
            else:
                print(f"OK (score: {result['final_score']:.1f})")
            results.append(result)
        except Exception as e:
            print(f"FAILED: {e}")
            results.append({"photo_id": photo["id"], "error": str(e)})

    return results


async def main():
    parser = argparse.ArgumentParser(
        description="Rescore photos for specific users",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("user_ids", nargs="+", help="User IDs to rescore")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the rescore (default is dry run)",
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Use production Supabase (requires env vars)",
    )

    args = parser.parse_args()

    # Check for OpenRouter API key
    if args.execute and not os.environ.get("OPENROUTER_API_KEY"):
        print("ERROR: Set OPENROUTER_API_KEY environment variable")
        sys.exit(1)

    print(f"{'=' * 60}")
    print("Photo Rescore Tool")
    print(f"{'=' * 60}")
    print(f"Environment: {'Production' if args.production else 'Local'}")
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}")
    print(f"Users: {len(args.user_ids)}")
    print(f"{'=' * 60}")

    # Initialize clients
    supabase = get_supabase_client(args.production)

    # Only import inference service if we're executing
    inference_service = None
    if args.execute:
        # Set required env vars for OpenRouterService
        if not args.production:
            os.environ.setdefault("SUPABASE_URL", "http://127.0.0.1:54321")
            os.environ.setdefault(
                "SUPABASE_SERVICE_KEY",
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0."
                "EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU",
            )
            os.environ.setdefault(
                "SUPABASE_JWT_SECRET",
                "super-secret-jwt-token-with-at-least-32-characters-long",
            )

        from api.services.openrouter import OpenRouterService

        inference_service = OpenRouterService()

    # Process each user
    all_results = []
    for user_id in args.user_ids:
        print(f"\nProcessing user: {user_id}")
        results = await rescore_user_photos(
            supabase, user_id, inference_service, dry_run=not args.execute
        )
        all_results.extend(results)

    # Summary
    print(f"\n{'=' * 60}")
    print("Summary")
    print(f"{'=' * 60}")

    if args.execute:
        success = [r for r in all_results if "error" not in r]
        failed = [r for r in all_results if "error" in r]
        print(f"Rescored: {len(success)} photos")
        print(f"Failed: {len(failed)} photos")
        if failed:
            print("\nFailed photos:")
            for r in failed:
                print(f"  - {r.get('photo_id', 'unknown')}: {r.get('error', 'unknown error')}")
    else:
        print("DRY RUN - no changes made")
        print("Run with --execute to perform actual rescore")


if __name__ == "__main__":
    asyncio.run(main())
