#!/usr/bin/env python3
"""
Test triage flow against production API with pre-uploaded files.

This script creates a new triage job using files that were previously uploaded
to Supabase Storage. This is useful for testing the streaming memory fix.

Prerequisites:
1. Files must already be uploaded to Supabase Storage
2. You need a valid JWT token from the webapp

Usage:
    # Test with the 16-photo batch from previous test
    python scripts/test_triage_production.py --token YOUR_JWT --files /tmp/triage_files2.json

    # Generate a new job ID
    python scripts/test_triage_production.py --token YOUR_JWT --files /tmp/triage_files2.json --new-job-id
"""

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

import httpx

API_URL = "https://photo-score-api.onrender.com"


def wake_up_render(client: httpx.Client) -> bool:
    """Wake up Render service if sleeping."""
    print("Waking up Render service...")
    max_attempts = 5
    for i in range(max_attempts):
        try:
            r = client.get(f"{API_URL}/docs", timeout=30)
            if r.status_code == 200:
                print(f"  Render is awake (attempt {i + 1})")
                return True
        except Exception as e:
            print(f"  Attempt {i + 1}/{max_attempts}: {e}")
        time.sleep(5)
    return False


def start_triage(
    client: httpx.Client,
    token: str,
    job_id: str,
    files: list[dict],
    user_id: str,
) -> dict | None:
    """Start a triage job with pre-uploaded files."""
    print(f"\nStarting triage job: {job_id}")
    print(f"  Files: {len(files)}")
    print(f"  User ID: {user_id}")

    try:
        r = client.post(
            f"{API_URL}/api/triage/start-from-storage",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "job_id": job_id,
                "files": [
                    {
                        "original_name": f["original_name"],
                        "storage_path": f["storage_path"],
                        "size": f["size"],
                    }
                    for f in files
                ],
                "target": "20%",
                "criteria": "standout",
                "passes": 1,
            },
            timeout=30,
        )
        print(f"  Response: {r.status_code}")
        data = r.json()
        if r.status_code == 200:
            print(f"  Credits deducted: {data.get('credits_deducted')}")
            return data
        else:
            print(f"  Error: {data}")
        return None
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def poll_status(
    client: httpx.Client,
    token: str,
    job_id: str,
    max_polls: int = 120,
    interval: int = 3,
) -> dict | None:
    """Poll triage job until complete."""
    print(f"\nPolling job status ({max_polls * interval}s max)...")

    for i in range(max_polls):
        try:
            r = client.get(
                f"{API_URL}/api/triage/{job_id}/status",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )

            if r.status_code != 200:
                print(f"  [{i + 1}] Status check failed: {r.status_code}")
                time.sleep(interval)
                continue

            data = r.json()
            status = data.get("status")
            progress = data.get("progress", {})
            phase = progress.get("phase", "unknown")
            step = progress.get("current_step", 0)
            total = progress.get("total_steps", 0)
            pct = progress.get("percentage", 0)

            print(f"  [{i + 1}] {status} | {phase} | {step}/{total} ({pct:.0f}%)")

            if status == "completed":
                print("\n  SUCCESS: Triage completed!")
                return data
            elif status == "failed":
                print(f"\n  FAILED: {data.get('error_message')}")
                return data
            elif status == "cancelled":
                print("\n  CANCELLED")
                return data

            time.sleep(interval)

        except Exception as e:
            print(f"  [{i + 1}] Error: {e}")
            time.sleep(interval)

    print("\n  TIMEOUT: Job did not complete in time")
    return None


def get_results(client: httpx.Client, token: str, job_id: str) -> dict | None:
    """Get triage results."""
    print(f"\nGetting results...")

    try:
        r = client.get(
            f"{API_URL}/api/triage/{job_id}/results",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )

        if r.status_code == 200:
            data = r.json()
            selected = data.get("selected_photos", [])
            print(f"  Selected: {len(selected)} photos")
            for p in selected[:5]:
                print(f"    - {p.get('original_filename')}")
            if len(selected) > 5:
                print(f"    ... and {len(selected) - 5} more")
            return data
        else:
            print(f"  Error: {r.status_code} - {r.json()}")
        return None
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Test triage on production")
    parser.add_argument("--token", required=True, help="JWT token")
    parser.add_argument("--files", required=True, type=Path, help="JSON file with uploaded files")
    parser.add_argument("--new-job-id", action="store_true", help="Generate new job ID")
    parser.add_argument("--job-id", help="Use specific job ID")
    parser.add_argument("--user-id", help="User ID (extracted from files path if not provided)")
    args = parser.parse_args()

    # Load files
    if not args.files.exists():
        print(f"ERROR: Files not found: {args.files}")
        sys.exit(1)

    with open(args.files) as f:
        files = json.load(f)

    print(f"Loaded {len(files)} files from {args.files}")

    # Extract user ID from storage path
    if args.user_id:
        user_id = args.user_id
    else:
        # Path format: triage/{user_id}/{job_id}/{file_uuid}.ext
        storage_path = files[0]["storage_path"]
        parts = storage_path.split("/")
        user_id = parts[1] if len(parts) >= 3 else "unknown"

    # Determine job ID
    if args.job_id:
        job_id = args.job_id
    elif args.new_job_id:
        job_id = str(uuid.uuid4())
    else:
        # Extract from storage path
        storage_path = files[0]["storage_path"]
        parts = storage_path.split("/")
        job_id = parts[2] if len(parts) >= 4 else str(uuid.uuid4())

    print(f"\n{'=' * 60}")
    print("Triage Production Test")
    print(f"{'=' * 60}")
    print(f"API: {API_URL}")
    print(f"Files: {len(files)}")
    print(f"Job ID: {job_id}")
    print(f"User ID: {user_id}")
    print(f"{'=' * 60}")

    # Create client
    client = httpx.Client(timeout=60)

    # Wake up Render
    if not wake_up_render(client):
        print("ERROR: Could not wake up Render service")
        sys.exit(1)

    # Start triage
    job_data = start_triage(client, args.token, job_id, files, user_id)
    if not job_data:
        print("\nFailed to start triage job")
        sys.exit(1)

    # Poll status
    final_status = poll_status(client, args.token, job_id)
    if not final_status:
        print("\nTriage did not complete")
        sys.exit(1)

    if final_status.get("status") != "completed":
        print(f"\nTriage ended with status: {final_status.get('status')}")
        sys.exit(1)

    # Get results
    results = get_results(client, args.token, job_id)

    print(f"\n{'=' * 60}")
    print("RESULT: {'PASSED' if results else 'FAILED'}")
    print(f"{'=' * 60}")

    sys.exit(0 if results else 1)


if __name__ == "__main__":
    main()
