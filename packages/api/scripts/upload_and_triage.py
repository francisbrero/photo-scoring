#!/usr/bin/env python3
"""Upload test photos to Supabase and run triage.

This script:
1. Uploads photos from test_photos/ to Supabase Storage
2. Starts a triage job with the uploaded files
3. Polls until complete
4. Shows results

Usage:
    python scripts/upload_and_triage.py --token YOUR_JWT_TOKEN
"""

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

import httpx
from supabase import create_client

# Config
API_URL = "https://photo-score-api.onrender.com"
SUPABASE_URL = "https://jbgkafsmdtotdrrgitzw.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpiZ2thZnNtZHRvdGRycmdpdHp3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzU2NjYxOTAsImV4cCI6MjA1MTI0MjE5MH0.J_0y0ML28ibHvtfGD2fDRBDzQtLHhNIgGpKPVPz6Grc"
TEST_PHOTOS_DIR = Path(__file__).parent.parent.parent.parent / "test_photos"
BUCKET = "photos"


def upload_photos(supabase, user_id: str, job_id: str, photos_dir: Path, limit: int = 16):
    """Upload photos to Supabase Storage."""
    extensions = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"}
    photos = sorted(
        [p for p in photos_dir.iterdir() if p.suffix.lower() in extensions and p.is_file()]
    )[:limit]

    print(f"Uploading {len(photos)} photos to storage...")
    uploaded = []

    for i, photo in enumerate(photos):
        # Generate unique storage path
        ext = photo.suffix.lower()
        unique_name = f"{uuid.uuid4()}{ext}"
        storage_path = f"triage/{user_id}/{job_id}/{unique_name}"

        print(f"  [{i + 1}/{len(photos)}] {photo.name} -> {storage_path}")

        # Upload
        with open(photo, "rb") as f:
            data = f.read()

        # Determine content type
        content_type = "image/jpeg"
        if ext in [".heic", ".heif"]:
            content_type = "image/heic"
        elif ext == ".png":
            content_type = "image/png"
        elif ext == ".webp":
            content_type = "image/webp"

        result = supabase.storage.from_(BUCKET).upload(
            storage_path, data, file_options={"content-type": content_type}
        )

        uploaded.append(
            {
                "original_name": photo.name,
                "storage_path": storage_path,
                "size": len(data),
            }
        )

    return uploaded


def start_triage(client: httpx.Client, token: str, job_id: str, files: list) -> dict | None:
    """Start a triage job."""
    print(f"\nStarting triage job: {job_id}")
    print(f"  Files: {len(files)}")

    response = client.post(
        f"{API_URL}/api/triage/start-from-storage",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "job_id": job_id,
            "files": files,
            "target": "20%",
            "criteria": "standout",
            "passes": 1,
        },
        timeout=30,
    )

    print(f"  Response: {response.status_code}")
    data = response.json()

    if response.status_code == 200:
        print(f"  Credits deducted: {data.get('credits_deducted')}")
        return data
    else:
        print(f"  Error: {data}")
        return None


def poll_status(client: httpx.Client, token: str, job_id: str, max_polls: int = 120) -> dict | None:
    """Poll until complete."""
    print(f"\nPolling status (max {max_polls * 3}s)...")

    for i in range(max_polls):
        response = client.get(
            f"{API_URL}/api/triage/{job_id}/status",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )

        if response.status_code != 200:
            print(f"  [{i + 1}] Error: {response.status_code}")
            time.sleep(3)
            continue

        data = response.json()
        status = data.get("status")
        progress = data.get("progress", {})
        phase = progress.get("phase", "unknown")
        step = progress.get("current_step", 0)
        total = progress.get("total_steps", 0)
        pct = progress.get("percentage", 0)

        print(f"  [{i + 1}] {status} | {phase} | {step}/{total} ({pct:.0f}%)")

        if status == "completed":
            return data
        elif status in ["failed", "cancelled"]:
            print(f"  Error: {data.get('error_message')}")
            return data

        time.sleep(3)

    print("  Timeout!")
    return None


def get_results(client: httpx.Client, token: str, job_id: str) -> dict | None:
    """Get triage results."""
    print("\nGetting results...")

    response = client.get(
        f"{API_URL}/api/triage/{job_id}/results",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    if response.status_code == 200:
        return response.json()
    else:
        print(f"  Error: {response.status_code} - {response.json()}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True, help="JWT token")
    parser.add_argument("--photos", type=Path, default=TEST_PHOTOS_DIR, help="Photos directory")
    parser.add_argument("--limit", type=int, default=16, help="Max photos to upload")
    args = parser.parse_args()

    # Extract user ID from token (it's in the 'sub' claim)
    import base64

    payload = args.token.split(".")[1]
    # Add padding if needed
    payload += "=" * (4 - len(payload) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload))
    user_id = claims["sub"]

    print(f"User ID: {user_id}")
    print(f"Photos dir: {args.photos}")

    # Create Supabase client with user's token for RLS
    supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    supabase.auth.set_session(args.token, "")

    # Generate job ID
    job_id = str(uuid.uuid4())
    print(f"Job ID: {job_id}")

    # Upload photos
    uploaded = upload_photos(supabase, user_id, job_id, args.photos, args.limit)
    print(f"\nUploaded {len(uploaded)} photos")

    # Save for debugging
    with open(f"/tmp/triage_files_test.json", "w") as f:
        json.dump(uploaded, f, indent=2)

    # Start triage
    client = httpx.Client(timeout=60)
    job_data = start_triage(client, args.token, job_id, uploaded)

    if not job_data:
        print("Failed to start triage")
        sys.exit(1)

    # Poll
    final = poll_status(client, args.token, job_id)

    if not final or final.get("status") != "completed":
        print(f"Triage did not complete: {final}")
        sys.exit(1)

    # Get results
    results = get_results(client, args.token, job_id)

    if results:
        selected = results.get("selected_photos", [])
        total = results.get("total_input", 0)
        print(f"\n{'=' * 50}")
        print(f"RESULTS: Selected {len(selected)}/{total} photos ({len(selected) * 100 // total}%)")
        print(f"{'=' * 50}")
        print("\nSelected photos:")
        for p in selected:
            print(f"  - {p.get('original_filename')}")
    else:
        print("Failed to get results")
        sys.exit(1)


if __name__ == "__main__":
    main()
