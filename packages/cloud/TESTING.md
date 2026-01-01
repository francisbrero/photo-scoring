# Testing Guide for Photo Scoring Cloud Backend

This document describes the testing strategy, setup, and best practices for the photo-scoring cloud backend.

## Table of Contents

- [Philosophy](#philosophy)
- [Test Categories](#test-categories)
- [Setup](#setup)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Fixtures Reference](#fixtures-reference)
- [Cost Considerations](#cost-considerations)

---

## Philosophy

### Real Infrastructure Over Mocks

**We prefer testing against real infrastructure** (local Supabase) rather than mocking database interactions. This approach:

- Catches real integration issues (schema mismatches, RLS policies, etc.)
- Tests actual SQL queries and constraints
- Validates the full request/response cycle
- Ensures migrations work correctly

### Exception: External API Costs

**Always mock external paid APIs** like OpenRouter to avoid unnecessary costs during testing. AI inference calls should be mocked with realistic response structures.

```python
# GOOD: Mock expensive external APIs
async def mock_analyze_image(self, image_data, image_hash):
    return {
        "composition": 0.7,
        "subject_strength": 0.8,
        "visual_appeal": 0.75,
        "sharpness": 0.9,
        "exposure_balance": 0.85,
        "noise_level": 0.1,
    }

monkeypatch.setattr(openrouter.OpenRouterService, "analyze_image", mock_analyze_image)
```

```python
# BAD: Don't mock database interactions
# Instead, use the real local Supabase instance
```

---

## Test Categories

### 1. Unit Tests (No Supabase Required)

Located in: `tests/test_*.py` (except integration/e2e files)

These tests:
- Test individual functions and classes in isolation
- Use mocked Supabase clients for dependency injection
- Run fast (~1-2 seconds total)
- Don't require any external services

**Files:**
- `test_health.py` - Health endpoint
- `test_credits.py` - Credit service logic
- `test_billing.py` - Billing endpoints
- `test_inference.py` - Inference service logic
- `test_photos.py` - Photo endpoint validation
- `test_image_processing.py` - Image handling utilities

### 2. Integration Tests (Requires Local Supabase)

Located in: `tests/test_integration.py`

These tests:
- Test API endpoints against real local Supabase
- Verify database operations, RLS policies, and constraints
- Create real users, upload real files, make real DB queries
- Clean up test data after each test

**Coverage:**
- Authentication flow (signup, login, token validation)
- Credits system (trial credits, balance, transactions)
- Photo upload and storage
- Photo scoring pipeline (with mocked AI)
- Explanation regeneration

### 3. End-to-End Tests (Requires Local Supabase)

Located in: `tests/test_e2e_user_journey.py`

These tests:
- Simulate complete user journeys
- Test the full flow from signup to photo scoring
- Verify all components work together correctly

**Scenarios:**
- Complete user journey: signup → trial credits → upload → score → view → regenerate
- Edge case: Cannot score without credits

---

## Setup

### Prerequisites

1. **Docker** - Required for local Supabase
2. **Supabase CLI** - Install with `brew install supabase/tap/supabase`
3. **Python dependencies** - Install with `uv sync`

### Starting Local Supabase

```bash
# From the repository root
cd /path/to/photo-scoring

# Start Supabase (first time takes longer to download images)
supabase start

# Verify it's running
supabase status
```

This starts:
- PostgreSQL database on port 54322
- Supabase API on port 54321
- Supabase Studio on port 54323
- Mailpit (email testing) on port 54324

### Environment Variables

For unit tests, no environment variables are needed (tests use mocked values).

For integration tests, the test fixtures automatically configure the correct local Supabase credentials. You don't need to set any environment variables.

### Applying Migrations

Migrations are automatically applied when you start Supabase. If you need to reset:

```bash
# Reset database and reapply all migrations
supabase db reset
```

---

## Running Tests

### All Tests (Requires Supabase)

```bash
cd packages/cloud
uv run pytest tests/ -v
```

### Unit Tests Only (No Supabase)

```bash
cd packages/cloud
uv run pytest tests/ -v \
  --ignore=tests/test_integration.py \
  --ignore=tests/test_e2e_user_journey.py
```

### Integration Tests Only

```bash
cd packages/cloud
uv run pytest tests/test_integration.py -v
```

### E2E Tests Only

```bash
cd packages/cloud
uv run pytest tests/test_e2e_user_journey.py -v
```

### Specific Test

```bash
cd packages/cloud
uv run pytest tests/test_integration.py::TestAuthIntegration::test_valid_token_accepted -v
```

### With Coverage

```bash
cd packages/cloud
uv run pytest tests/ --cov=api --cov-report=term-missing
```

### Automatic Skip When Supabase Not Running

Integration tests automatically skip if local Supabase is not running:

```
SKIPPED [1] tests/conftest_integration.py:45: Local Supabase not running. Start with: supabase start
```

---

## Writing Tests

### Unit Test Template

```python
"""Tests for [feature]."""

import pytest
from unittest.mock import MagicMock, patch


def test_feature_does_something(client, auth_headers):
    """Test that [feature] does [expected behavior]."""
    with patch("api.dependencies.create_client") as mock_create:
        mock_supabase = MagicMock()
        mock_create.return_value = mock_supabase

        # Setup mock responses
        mock_supabase.table().select().eq().execute.return_value.data = [...]

        # Make request
        response = client.get("/api/endpoint", headers=auth_headers)

        # Assert
        assert response.status_code == 200
        assert response.json()["key"] == "expected_value"
```

### Integration Test Template

```python
"""Integration tests for [feature]."""

import pytest
from io import BytesIO

from .conftest_integration import requires_supabase  # noqa: E402


@requires_supabase
class TestFeatureIntegration:
    """Test [feature] with local Supabase."""

    def test_feature_works(self, integration_client, auth_headers, supabase_admin):
        """Test that [feature] works end-to-end."""
        # Trigger trial credits if needed
        integration_client.get("/api/auth/me", headers=auth_headers)

        # Perform action
        response = integration_client.post(
            "/api/endpoint",
            headers=auth_headers,
            json={"key": "value"},
        )

        # Assert API response
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "expected_value"

        # Optionally verify database state directly
        db_result = supabase_admin.table("table_name").select("*").execute()
        assert len(db_result.data) == 1
```

### Mocking OpenRouter (AI Service)

**Always mock OpenRouter to avoid API costs:**

```python
def test_scoring_with_mocked_ai(
    self, integration_client, auth_headers, sample_jpeg_bytes, monkeypatch
):
    """Test scoring with mocked AI service."""
    from api.services import openrouter

    # Mock the image analysis
    async def mock_analyze_image(self, image_data, image_hash):
        return {
            "composition": 0.7,
            "subject_strength": 0.8,
            "visual_appeal": 0.75,
            "sharpness": 0.9,
            "exposure_balance": 0.85,
            "noise_level": 0.1,
        }

    # Mock the metadata extraction
    async def mock_analyze_metadata(self, image_data, image_hash):
        return {
            "description": "A test photograph",
            "location_name": "Test Location",
            "location_country": "Test Country",
        }

    monkeypatch.setattr(
        openrouter.OpenRouterService, "analyze_image", mock_analyze_image
    )
    monkeypatch.setattr(
        openrouter.OpenRouterService, "analyze_image_metadata", mock_analyze_metadata
    )

    # Now test scoring - it will use mocked AI
    # ... rest of test
```

### Testing Credit Deduction

```python
def test_scoring_deducts_credit(self, integration_client, auth_headers, ...):
    """Verify that scoring deducts exactly 1 credit."""
    # Get initial balance
    integration_client.get("/api/auth/me", headers=auth_headers)  # Grant trial
    initial = integration_client.get("/api/billing/balance", headers=auth_headers)
    initial_credits = initial.json()["balance"]

    # Score a photo (with mocked AI)
    # ...

    # Verify credit deducted
    final = integration_client.get("/api/billing/balance", headers=auth_headers)
    assert final.json()["balance"] == initial_credits - 1
```

### Testing Insufficient Credits

```python
def test_insufficient_credits_rejected(
    self, integration_client, auth_headers, supabase_admin, test_user
):
    """Verify 402 when user has no credits."""
    # Set credits to 0
    supabase_admin.table("credits").update(
        {"balance": 0}
    ).eq("user_id", test_user["id"]).execute()

    # Try to score
    response = integration_client.post(f"/api/photos/{photo_id}/score", headers=auth_headers)

    assert response.status_code == 402
    assert "Insufficient credits" in response.json()["detail"]
```

---

## Fixtures Reference

### From `conftest.py` (Unit Tests)

| Fixture | Description |
|---------|-------------|
| `client` | FastAPI TestClient with mocked settings |
| `auth_token` | Valid JWT token string |
| `auth_headers` | Dict with `Authorization: Bearer <token>` |

### From `conftest_integration.py` (Integration Tests)

| Fixture | Description |
|---------|-------------|
| `supabase_admin` | Supabase client with service role (admin access) |
| `integration_client` | FastAPI TestClient connected to local Supabase |
| `test_user` | Creates a test user, yields user dict, deletes on cleanup |
| `test_user_token` | JWT token for the test user |
| `auth_headers` | Auth headers for test user |
| `sample_jpeg_bytes` | Valid minimal JPEG image bytes |
| `cleanup_storage` | Cleans up uploaded files after test |

### Constants

```python
from tests.conftest_integration import (
    LOCAL_SUPABASE_URL,        # http://127.0.0.1:54321
    LOCAL_SUPABASE_SERVICE_KEY, # Service role JWT
    LOCAL_JWT_SECRET,          # JWT signing secret
    requires_supabase,         # Skip decorator
)
```

---

## Cost Considerations

### OpenRouter API Costs

- **Cost per image**: ~$0.005 (7 API calls)
- **Never call OpenRouter in tests** without explicit need
- **Always mock** `OpenRouterService.analyze_image` and `analyze_image_metadata`

### When Real API Calls Are Needed

For rare cases where you need to test actual AI integration:

1. Create a separate test file: `tests/test_real_api.py`
2. Mark with a custom marker: `@pytest.mark.real_api`
3. Skip by default: `pytest.mark.skipif(not os.getenv("RUN_REAL_API_TESTS"))`
4. Document expected costs in the test docstring

```python
@pytest.mark.real_api
@pytest.mark.skipif(
    not os.getenv("RUN_REAL_API_TESTS"),
    reason="Skipping real API test to avoid costs"
)
def test_real_openrouter_integration():
    """Test actual OpenRouter integration.

    WARNING: This test costs approximately $0.005 per run.
    Run with: RUN_REAL_API_TESTS=1 pytest tests/test_real_api.py -v
    """
    # ... actual API test
```

### Local Supabase Costs

Local Supabase is **free** - it runs entirely on your machine via Docker. Use it liberally for integration tests.

---

## Troubleshooting

### Tests Fail with "Supabase not running"

```bash
supabase start
supabase status  # Verify it's running
```

### Tests Fail with "Invalid JWT"

The local Supabase credentials may have changed. Check:

```bash
supabase status --output json | jq '.SERVICE_ROLE_KEY'
```

Update `LOCAL_SUPABASE_SERVICE_KEY` in `conftest_integration.py` if different.

### Tests Leave Orphaned Data

Tests should clean up after themselves. If you have orphaned data:

```bash
supabase db reset  # WARNING: Deletes all data
```

### Integration Tests Fail When Run With Unit Tests

This shouldn't happen with current setup, but if it does:

1. Check that `get_settings.cache_clear()` is called in fixtures
2. Verify fixtures don't have `scope="session"` that causes state leakage
3. Run tests in isolation to identify the conflict

---

## Test Coverage Goals

| Category | Current | Target |
|----------|---------|--------|
| Auth endpoints | 100% | 100% |
| Credits/Billing | 90% | 95% |
| Photo upload | 85% | 95% |
| Photo scoring | 80% | 90% |
| Error handling | 70% | 85% |

Run coverage report:
```bash
uv run pytest tests/ --cov=api --cov-report=html
open htmlcov/index.html
```
