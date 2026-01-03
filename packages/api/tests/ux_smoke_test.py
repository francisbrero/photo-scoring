#!/usr/bin/env python3
"""
UX Smoke Tests for Photo Scoring API

Run against local, staging, or production environments to verify
critical user flows work correctly.

Usage:
    # Test local
    python ux_smoke_test.py --url http://localhost:8000

    # Test staging/production
    python ux_smoke_test.py --url https://your-api.vercel.app --token YOUR_JWT

    # With a test image
    python ux_smoke_test.py --url https://api.example.com --token JWT --image test.jpg
"""

import argparse
import base64
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx


@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: float
    message: str = ""
    details: dict | None = None


class UXSmokeTest:
    """Smoke tests for the Photo Scoring API."""

    def __init__(self, base_url: str, token: str | None = None, verbose: bool = False):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.verbose = verbose
        self.results: list[TestResult] = []

    @property
    def headers(self) -> dict:
        """Get request headers with auth if available."""
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"  → {msg}")

    def _run_test(self, name: str, test_fn) -> TestResult:
        """Run a test function and capture results."""
        start = time.time()
        try:
            result = test_fn()
            duration = (time.time() - start) * 1000
            if isinstance(result, tuple):
                passed, message, details = result
            else:
                passed, message, details = result, "", None
            return TestResult(name, passed, duration, message, details)
        except Exception as e:
            duration = (time.time() - start) * 1000
            return TestResult(name, False, duration, str(e))

    # ==================== Health Tests ====================

    def test_health_endpoint(self) -> tuple[bool, str, dict | None]:
        """Test basic health endpoint."""
        self._log("GET /health")
        r = httpx.get(f"{self.base_url}/health", timeout=10)
        if r.status_code == 200:
            return True, f"Status {r.status_code}", r.json()
        return False, f"Expected 200, got {r.status_code}", None

    def test_api_health(self) -> tuple[bool, str, dict | None]:
        """Test API health endpoint."""
        self._log("GET /api/health")
        r = httpx.get(f"{self.base_url}/api/health", timeout=10)
        if r.status_code == 200:
            return True, f"Status {r.status_code}", r.json()
        return False, f"Expected 200, got {r.status_code}", None

    def test_openapi_docs(self) -> tuple[bool, str, dict | None]:
        """Test OpenAPI docs are accessible."""
        self._log("GET /docs")
        r = httpx.get(f"{self.base_url}/docs", timeout=10)
        if r.status_code == 200 and "swagger" in r.text.lower():
            return True, "Swagger UI loaded", None
        return False, f"Status {r.status_code}", None

    # ==================== Auth Tests ====================

    def test_auth_required(self) -> tuple[bool, str, dict | None]:
        """Test that endpoints require authentication."""
        self._log("GET /api/photos (no auth)")
        r = httpx.get(f"{self.base_url}/api/photos", timeout=10)
        if r.status_code == 401:
            return True, "Correctly requires auth", None
        return False, f"Expected 401, got {r.status_code}", None

    def test_auth_with_token(self) -> tuple[bool, str, dict | None]:
        """Test that valid token grants access."""
        if not self.token:
            return True, "Skipped (no token provided)", None

        self._log("GET /api/photos (with auth)")
        r = httpx.get(f"{self.base_url}/api/photos", headers=self.headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return True, f"Got {data.get('total', 0)} photos", data
        return False, f"Expected 200, got {r.status_code}", None

    # ==================== Credits Tests ====================

    def test_credits_balance(self) -> tuple[bool, str, dict | None]:
        """Test credits balance endpoint."""
        if not self.token:
            return True, "Skipped (no token provided)", None

        self._log("GET /api/credits/balance")
        r = httpx.get(f"{self.base_url}/api/credits/balance", headers=self.headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return True, f"Balance: {data.get('balance', 'unknown')}", data
        return False, f"Expected 200, got {r.status_code}", None

    # ==================== Photo List Tests ====================

    def test_photos_list(self) -> tuple[bool, str, dict | None]:
        """Test photo listing with pagination."""
        if not self.token:
            return True, "Skipped (no token provided)", None

        self._log("GET /api/photos?limit=5")
        r = httpx.get(f"{self.base_url}/api/photos?limit=5", headers=self.headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return True, f"Got {len(data.get('photos', []))} photos", data
        return False, f"Expected 200, got {r.status_code}", None

    def test_photos_sorting(self) -> tuple[bool, str, dict | None]:
        """Test photo sorting options."""
        if not self.token:
            return True, "Skipped (no token provided)", None

        self._log("GET /api/photos?sort_by=final_score&sort_order=desc")
        r = httpx.get(
            f"{self.base_url}/api/photos?sort_by=final_score&sort_order=desc",
            headers=self.headers,
            timeout=10,
        )
        if r.status_code == 200:
            return True, "Sorting works", None
        return False, f"Expected 200, got {r.status_code}", None

    # ==================== Rescore Tests ====================

    def test_rescore_endpoint(self) -> tuple[bool, str, dict | None]:
        """Test rescore endpoint with default weights."""
        if not self.token:
            return True, "Skipped (no token provided)", None

        self._log("POST /api/photos/rescore")
        r = httpx.post(
            f"{self.base_url}/api/photos/rescore",
            headers=self.headers,
            json={},
            timeout=30,
        )
        if r.status_code == 200:
            data = r.json()
            return (
                True,
                f"Rescored {data.get('total_rescored', 0)} photos",
                data,
            )
        return False, f"Expected 200, got {r.status_code}: {r.text}", None

    def test_rescore_custom_weights(self) -> tuple[bool, str, dict | None]:
        """Test rescore with custom weights."""
        if not self.token:
            return True, "Skipped (no token provided)", None

        self._log("POST /api/photos/rescore (custom weights)")
        r = httpx.post(
            f"{self.base_url}/api/photos/rescore",
            headers=self.headers,
            json={
                "weights": {
                    "composition": 0.5,
                    "subject_strength": 0.3,
                    "visual_appeal": 0.2,
                    "aesthetic_weight": 0.7,
                    "technical_weight": 0.3,
                }
            },
            timeout=30,
        )
        if r.status_code == 200:
            data = r.json()
            return True, f"Custom weights applied", data
        return False, f"Expected 200, got {r.status_code}", None

    # ==================== Score Direct Tests ====================

    def test_score_direct(self, image_path: str | None = None) -> tuple[bool, str, dict | None]:
        """Test direct scoring endpoint."""
        if not self.token:
            return True, "Skipped (no token provided)", None
        if not image_path:
            return True, "Skipped (no image provided)", None

        self._log(f"POST /api/photos/score-direct ({image_path})")

        # Read and encode image
        img_bytes = Path(image_path).read_bytes()
        b64_image = base64.b64encode(img_bytes).decode()

        r = httpx.post(
            f"{self.base_url}/api/photos/score-direct",
            headers=self.headers,
            json={"image_data": b64_image},
            timeout=60,
        )
        if r.status_code == 200:
            data = r.json()
            return (
                True,
                f"Score: {data.get('final_score', 'unknown')}, cached: {data.get('cached')}",
                data,
            )
        elif r.status_code == 402:
            return False, "Insufficient credits", None
        return False, f"Expected 200, got {r.status_code}: {r.text[:200]}", None

    # ==================== Error Handling Tests ====================

    def test_404_handling(self) -> tuple[bool, str, dict | None]:
        """Test 404 for non-existent resources."""
        if not self.token:
            return True, "Skipped (no token provided)", None

        self._log("GET /api/photos/nonexistent-id-12345")
        r = httpx.get(
            f"{self.base_url}/api/photos/nonexistent-id-12345",
            headers=self.headers,
            timeout=10,
        )
        if r.status_code == 404:
            return True, "Correctly returns 404", None
        return False, f"Expected 404, got {r.status_code}", None

    def test_validation_error(self) -> tuple[bool, str, dict | None]:
        """Test validation errors return 422."""
        if not self.token:
            return True, "Skipped (no token provided)", None

        self._log("GET /api/photos?limit=9999")
        r = httpx.get(
            f"{self.base_url}/api/photos?limit=9999",
            headers=self.headers,
            timeout=10,
        )
        if r.status_code == 422:
            return True, "Correctly validates input", None
        return False, f"Expected 422, got {r.status_code}", None

    # ==================== Run All Tests ====================

    def run_all(self, image_path: str | None = None) -> list[TestResult]:
        """Run all smoke tests."""
        tests = [
            ("Health Endpoint", self.test_health_endpoint),
            ("API Health", self.test_api_health),
            ("OpenAPI Docs", self.test_openapi_docs),
            ("Auth Required", self.test_auth_required),
            ("Auth With Token", self.test_auth_with_token),
            ("Credits Balance", self.test_credits_balance),
            ("Photos List", self.test_photos_list),
            ("Photos Sorting", self.test_photos_sorting),
            ("Rescore Default", self.test_rescore_endpoint),
            ("Rescore Custom Weights", self.test_rescore_custom_weights),
            ("404 Handling", self.test_404_handling),
            ("Validation Error", self.test_validation_error),
        ]

        # Add image-dependent tests
        if image_path:
            tests.append(("Score Direct", lambda: self.test_score_direct(image_path)))

        print(f"\n{'=' * 60}")
        print(f"Photo Scoring API - UX Smoke Tests")
        print(f"{'=' * 60}")
        print(f"Target: {self.base_url}")
        print(f"Auth: {'Yes' if self.token else 'No'}")
        print(f"{'=' * 60}\n")

        for name, test_fn in tests:
            result = self._run_test(name, test_fn)
            self.results.append(result)

            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status} | {result.name} ({result.duration_ms:.0f}ms)")
            if result.message:
                print(f"       {result.message}")
            if not result.passed and result.details:
                print(f"       Details: {json.dumps(result.details, indent=2)[:200]}")

        # Summary
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        print(f"\n{'=' * 60}")
        print(f"Results: {passed}/{total} tests passed")
        print(f"{'=' * 60}\n")

        return self.results


def check_api_reachable(url: str) -> bool:
    """Check if the API is reachable."""
    try:
        httpx.get(url, timeout=5)
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="UX Smoke Tests for Photo Scoring API")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--token",
        help="JWT token for authenticated requests",
    )
    parser.add_argument(
        "--image",
        help="Path to test image for score-direct test",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--skip-reachability",
        action="store_true",
        help="Skip initial reachability check",
    )
    args = parser.parse_args()

    # Check if API is reachable first
    if not args.skip_reachability and not check_api_reachable(args.url):
        print(f"\n⚠️  Cannot reach API at {args.url}")
        print("\nIf testing locally, start the API first:")
        print("  cd packages/api && uv run uvicorn api.main:app --reload")
        print("\nOr specify a different URL:")
        print("  python ux_smoke_test.py --url https://your-api.vercel.app")
        print("\nTo skip this check, use --skip-reachability")
        sys.exit(1)

    tester = UXSmokeTest(args.url, args.token, args.verbose)
    results = tester.run_all(args.image)

    # Exit with error code if any tests failed
    failed = sum(1 for r in results if not r.passed)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
