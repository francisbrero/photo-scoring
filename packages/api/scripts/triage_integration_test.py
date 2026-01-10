#!/usr/bin/env python3
"""Integration test for the Triage flow.

Tests the full triage flow: upload to storage, start job, poll status, get results.

Usage:
    # Against local (default)
    python scripts/triage_integration_test.py

    # Against production
    python scripts/triage_integration_test.py --api-url https://photo-score-api.onrender.com

    # With specific photos directory
    python scripts/triage_integration_test.py --photos /path/to/photos
"""

import argparse
import os
import sys
import time
import uuid
from pathlib import Path

import httpx

# Default test photos path (relative to repo root)
DEFAULT_PHOTOS_PATH = Path(__file__).parent.parent.parent.parent / "test_photos"


def get_test_photos(photos_path: Path, limit: int = 16) -> list[Path]:
    """Get test photos from the specified directory."""
    if not photos_path.exists():
        print(f"ERROR: Photos directory not found: {photos_path}")
        sys.exit(1)

    # Get image files
    extensions = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"}
    photos = [p for p in photos_path.iterdir() if p.suffix.lower() in extensions and p.is_file()]

    if not photos:
        print(f"ERROR: No image files found in {photos_path}")
        sys.exit(1)

    # Limit to specified count
    photos = sorted(photos)[:limit]
    print(f"Found {len(photos)} test photos")
    return photos


def upload_to_storage_mock(photos: list[Path], user_id: str, job_id: str) -> list[dict]:
    """
    In a real test, this would upload to Supabase Storage.
    For now, we simulate by returning mock storage paths.
    The actual upload happens via the webapp.
    """
    files = []
    for photo in photos:
        files.append(
            {
                "original_name": photo.name,
                "storage_path": f"triage/{user_id}/{job_id}/{uuid.uuid4()}{photo.suffix.lower()}",
                "size": photo.stat().st_size,
            }
        )
    return files


def test_start_triage(
    client: httpx.Client,
    api_url: str,
    token: str,
    files: list[dict],
    job_id: str,
) -> dict | None:
    """Start a triage job with pre-uploaded files."""
    print("\n=== Starting Triage Job ===")
    print(f"Job ID: {job_id}")
    print(f"Files: {len(files)}")

    try:
        response = client.post(
            f"{api_url}/api/triage/start-from-storage",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "job_id": job_id,
                "files": files,
                "target": "20%",
                "criteria": "standout",
                "passes": 1,
            },
            timeout=30.0,
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {data}")

        if response.status_code == 200:
            return data
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def test_poll_status(
    client: httpx.Client,
    api_url: str,
    token: str,
    job_id: str,
    max_polls: int = 60,
    poll_interval: int = 2,
) -> dict | None:
    """Poll triage job status until complete or failed."""
    print("\n=== Polling Triage Status ===")

    for i in range(max_polls):
        try:
            response = client.get(
                f"{api_url}/api/triage/{job_id}/status",
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code != 200:
                print(f"[{i + 1}] Status check failed: {response.status_code}")
                time.sleep(poll_interval)
                continue

            data = response.json()
            status = data.get("status")
            phase = data.get("progress", {}).get("phase", "unknown")
            step = data.get("progress", {}).get("current_step", 0)
            total = data.get("progress", {}).get("total_steps", 0)

            print(f"[{i + 1}] Status: {status}, Phase: {phase}, Step: {step}/{total}")

            if status == "completed":
                print("Triage completed successfully!")
                return data
            elif status == "failed":
                print(f"Triage failed: {data.get('error_message')}")
                return data
            elif status == "cancelled":
                print("Triage was cancelled")
                return data

            time.sleep(poll_interval)

        except Exception as e:
            print(f"[{i + 1}] Error polling: {e}")
            time.sleep(poll_interval)

    print("Triage timed out!")
    return None


def test_get_results(
    client: httpx.Client,
    api_url: str,
    token: str,
    job_id: str,
) -> dict | None:
    """Get triage results."""
    print("\n=== Getting Triage Results ===")

    try:
        response = client.get(
            f"{api_url}/api/triage/{job_id}/results",
            headers={"Authorization": f"Bearer {token}"},
        )
        print(f"Status: {response.status_code}")
        data = response.json()

        if response.status_code == 200:
            selected = data.get("selected_photos", [])
            print(f"Selected photos: {len(selected)}")
            for photo in selected[:5]:
                print(f"  - {photo.get('original_filename')}")
            if len(selected) > 5:
                print(f"  ... and {len(selected) - 5} more")
            return data
        else:
            print(f"Response: {data}")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Integration test for Triage flow")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--token",
        help="JWT token for authentication. If not provided, uses SUPABASE_TEST_TOKEN env var.",
    )
    parser.add_argument(
        "--photos",
        type=Path,
        default=DEFAULT_PHOTOS_PATH,
        help=f"Path to test photos directory (default: {DEFAULT_PHOTOS_PATH})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=16,
        help="Maximum number of photos to test with (default: 16)",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip upload step (assumes files already in storage)",
    )
    args = parser.parse_args()

    # Get token
    token = args.token or os.environ.get("SUPABASE_TEST_TOKEN")
    if not token:
        print("ERROR: No token provided. Use --token or set SUPABASE_TEST_TOKEN env var.")
        print("\nTo get a token:")
        print("1. Open browser dev tools on your app")
        print("2. Go to Application > Local Storage > your-supabase-url")
        print("3. Find the 'sb-xxx-auth-token' key")
        print("4. Copy the 'access_token' value")
        sys.exit(1)

    # Get test photos
    photos = get_test_photos(args.photos, args.limit)

    # Create HTTP client
    client = httpx.Client(timeout=30.0)
    api_url = args.api_url.rstrip("/")

    print(f"\n{'=' * 60}")
    print("Triage Integration Test")
    print(f"API URL: {api_url}")
    print(f"Photos: {len(photos)}")
    print(f"{'=' * 60}")

    # Generate job ID and mock user ID
    job_id = str(uuid.uuid4())
    user_id = "test-user-" + str(uuid.uuid4())[:8]

    # Step 1: Simulate upload (in real test, this would upload to Supabase)
    print("\n=== Preparing Files ===")
    files = upload_to_storage_mock(photos, user_id, job_id)
    print(f"Prepared {len(files)} files for job {job_id}")

    # Note: For actual E2E testing, you would need to:
    # 1. Upload files to Supabase Storage first
    # 2. Then call start-from-storage with the real paths
    print("\nNOTE: This test uses mock storage paths.")
    print("For full E2E testing, use the webapp or upload files to Supabase first.")

    # Step 2: Start triage
    job_data = test_start_triage(client, api_url, token, files, job_id)
    if not job_data:
        print("\nFailed to start triage job")
        sys.exit(1)

    # Step 3: Poll status
    final_status = test_poll_status(client, api_url, token, job_id)
    if not final_status:
        print("\nTriage did not complete in time")
        sys.exit(1)

    if final_status.get("status") != "completed":
        print(f"\nTriage ended with status: {final_status.get('status')}")
        sys.exit(1)

    # Step 4: Get results
    results = test_get_results(client, api_url, token, job_id)

    print(f"\n{'=' * 60}")
    print("Test Results Summary")
    print(f"{'=' * 60}")
    print(f"  Job ID: {job_id}")
    print(f"  Input photos: {len(photos)}")
    print(f"  Selected: {len(results.get('selected_photos', [])) if results else 'N/A'}")
    print(f"  Status: {'PASSED' if results else 'FAILED'}")
    print(f"{'=' * 60}")

    sys.exit(0 if results else 1)


if __name__ == "__main__":
    main()
