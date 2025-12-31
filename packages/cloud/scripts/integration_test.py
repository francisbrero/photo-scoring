#!/usr/bin/env python3
"""Integration test for the Photo Score API.

This script tests the full flow: auth, upload, and scoring.
Run against local or production API.

Usage:
    # Against local (default)
    python scripts/integration_test.py

    # Against production
    python scripts/integration_test.py --api-url https://photo-score-api.onrender.com

    # With a specific test image
    python scripts/integration_test.py --image /path/to/test.jpg
"""

import argparse
import base64
import os
import sys
from pathlib import Path

import httpx
from PIL import Image
from io import BytesIO


def create_test_image() -> bytes:
    """Create a simple test image (red square) as JPEG bytes."""
    img = Image.new("RGB", (100, 100), color="red")
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def test_health(client: httpx.Client, api_url: str) -> bool:
    """Test health endpoint."""
    print("\n=== Testing Health Endpoint ===")
    try:
        response = client.get(f"{api_url}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_auth_me(client: httpx.Client, api_url: str, token: str) -> dict | None:
    """Test /api/auth/me endpoint."""
    print("\n=== Testing Auth Endpoint ===")
    try:
        response = client.get(
            f"{api_url}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
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


def test_upload(
    client: httpx.Client, api_url: str, token: str, image_data: bytes, filename: str
) -> str | None:
    """Test photo upload endpoint. Returns photo_id on success."""
    print("\n=== Testing Upload Endpoint ===")
    print(f"Image size: {len(image_data)} bytes")
    print(f"First 20 bytes: {image_data[:20]}")

    try:
        response = client.post(
            f"{api_url}/api/photos/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (filename, image_data, "image/jpeg")},
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {data}")

        if response.status_code == 200:
            return data.get("id")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def test_score(client: httpx.Client, api_url: str, token: str, photo_id: str) -> dict | None:
    """Test photo scoring endpoint."""
    print("\n=== Testing Score Endpoint ===")
    print(f"Photo ID: {photo_id}")

    try:
        response = client.post(
            f"{api_url}/api/photos/{photo_id}/score",
            headers={"Authorization": f"Bearer {token}"},
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


def test_inference_analyze(
    client: httpx.Client, api_url: str, token: str, image_data: bytes
) -> dict | None:
    """Test direct inference/analyze endpoint."""
    print("\n=== Testing Inference Analyze Endpoint ===")
    print(f"Image size: {len(image_data)} bytes")

    # Encode as base64
    b64_data = base64.b64encode(image_data).decode("utf-8")
    print(f"Base64 length: {len(b64_data)}")

    try:
        response = client.post(
            f"{api_url}/api/inference/analyze",
            headers={"Authorization": f"Bearer {token}"},
            json={"image_data": b64_data},
            timeout=120.0,
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


def test_list_photos(client: httpx.Client, api_url: str, token: str) -> list | None:
    """Test listing photos endpoint."""
    print("\n=== Testing List Photos Endpoint ===")

    try:
        response = client.get(
            f"{api_url}/api/photos",
            headers={"Authorization": f"Bearer {token}"},
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {data}")

        if response.status_code == 200:
            return data.get("photos", [])
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Integration test for Photo Score API")
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
        "--image",
        type=Path,
        help="Path to test image. If not provided, creates a simple test image.",
    )
    parser.add_argument(
        "--skip-inference",
        action="store_true",
        help="Skip inference test (which costs credits)",
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

    # Get or create test image
    if args.image:
        if not args.image.exists():
            print(f"ERROR: Image file not found: {args.image}")
            sys.exit(1)
        image_data = args.image.read_bytes()
        filename = args.image.name
        print(f"Using image: {args.image} ({len(image_data)} bytes)")
    else:
        image_data = create_test_image()
        filename = "test_image.jpg"
        print(f"Created test image: {len(image_data)} bytes")

    # Verify image is valid
    try:
        img = Image.open(BytesIO(image_data))
        print(f"Image format: {img.format}, size: {img.size}, mode: {img.mode}")
    except Exception as e:
        print(f"ERROR: Invalid image data: {e}")
        sys.exit(1)

    # Create HTTP client
    client = httpx.Client(timeout=30.0)
    api_url = args.api_url.rstrip("/")

    print(f"\n{'=' * 60}")
    print(f"Integration Test for Photo Score API")
    print(f"API URL: {api_url}")
    print(f"{'=' * 60}")

    results = {}

    # Test 1: Health
    results["health"] = test_health(client, api_url)

    # Test 2: Auth
    auth_data = test_auth_me(client, api_url, token)
    results["auth"] = auth_data is not None
    if auth_data:
        print(f"  User ID: {auth_data.get('user_id')}")
        print(f"  Credits: {auth_data.get('credit_balance')}")

    # Test 3: List photos (before upload)
    photos = test_list_photos(client, api_url, token)
    results["list_photos"] = photos is not None

    # Test 4: Upload
    photo_id = test_upload(client, api_url, token, image_data, filename)
    results["upload"] = photo_id is not None

    # Test 5: Score (if upload succeeded and not skipped)
    if photo_id and not args.skip_inference:
        score_data = test_score(client, api_url, token, photo_id)
        results["score"] = score_data is not None
        if score_data:
            print(f"  Final Score: {score_data.get('final_score')}")
            print(f"  Credits Remaining: {score_data.get('credits_remaining')}")
    else:
        results["score"] = None
        print("\n=== Skipping Score Test ===")

    # Test 6: Direct inference (if not skipped)
    if not args.skip_inference:
        inference_data = test_inference_analyze(client, api_url, token, image_data)
        results["inference"] = inference_data is not None
    else:
        results["inference"] = None
        print("\n=== Skipping Inference Test ===")

    # Summary
    print(f"\n{'=' * 60}")
    print("Test Results Summary")
    print(f"{'=' * 60}")

    all_passed = True
    for test_name, passed in results.items():
        if passed is None:
            status = "SKIPPED"
        elif passed:
            status = "PASSED ✓"
        else:
            status = "FAILED ✗"
            all_passed = False
        print(f"  {test_name}: {status}")

    print(f"{'=' * 60}")
    if all_passed:
        print("All tests passed!")
        sys.exit(0)
    else:
        print("Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
