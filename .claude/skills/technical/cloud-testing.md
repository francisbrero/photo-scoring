---
description: Guidelines for writing tests for the cloud backend API
globs:
  - "packages/api/tests/**/*.py"
  - "packages/api/api/**/*.py"
alwaysApply: false
---

# Cloud Backend Testing Guide

## Philosophy

### DO: Test Against Real Infrastructure

Use local Supabase for integration tests instead of mocking database calls:

```python
@requires_supabase
class TestFeatureIntegration:
    def test_feature(self, integration_client, auth_headers, supabase_admin):
        # Real database operations
        response = integration_client.post("/api/endpoint", headers=auth_headers)

        # Verify in real database
        db_result = supabase_admin.table("table").select("*").execute()
```

### DON'T: Call OpenRouter (Costs Money!)

**Always mock OpenRouter** to avoid API costs (~$0.005/image):

```python
def test_scoring(self, integration_client, auth_headers, monkeypatch):
    from api.services import openrouter

    async def mock_analyze_image(self, image_data, image_hash):
        return {
            "composition": 0.7,
            "subject_strength": 0.8,
            "visual_appeal": 0.75,
            "sharpness": 0.9,
            "exposure_balance": 0.85,
            "noise_level": 0.1,
        }

    async def mock_analyze_metadata(self, image_data, image_hash):
        return {
            "description": "Test photo",
            "location_name": "Test Location",
            "location_country": "Test Country",
        }

    monkeypatch.setattr(openrouter.OpenRouterService, "analyze_image", mock_analyze_image)
    monkeypatch.setattr(openrouter.OpenRouterService, "analyze_image_metadata", mock_analyze_metadata)

    # Now test scoring - uses mocked AI
```

---

## Test Structure

```
packages/api/tests/
├── conftest.py                 # Shared fixtures (unit tests)
├── conftest_integration.py     # Integration test fixtures
├── test_health.py              # Health endpoint (unit)
├── test_credits.py             # Credit service (unit)
├── test_billing.py             # Billing endpoints (unit)
├── test_inference.py           # Inference service (unit)
├── test_photos.py              # Photo endpoints (unit)
├── test_integration.py         # Integration tests
└── test_e2e_user_journey.py    # E2E tests
```

---

## Available Fixtures

### Unit Test Fixtures (conftest.py)

```python
def test_something(client, auth_headers):
    response = client.get("/api/endpoint", headers=auth_headers)
```

### Integration Test Fixtures (conftest_integration.py)

```python
from .conftest_integration import requires_supabase

@requires_supabase
class TestSomething:
    def test_feature(
        self,
        integration_client,  # FastAPI TestClient → local Supabase
        auth_headers,        # JWT auth headers
        test_user,           # Dict with id, email, password
        supabase_admin,      # Admin Supabase client
        sample_jpeg_bytes,   # Valid JPEG image bytes
        cleanup_storage,     # Auto-cleanup uploaded files
    ):
        pass
```

---

## Common Patterns

### Test Authentication Required

```python
def test_endpoint_requires_auth(client):
    response = client.get("/api/photos")
    assert response.status_code == 401
```

### Test With Auth

```python
def test_endpoint_with_auth(client, auth_headers):
    response = client.get("/api/photos", headers=auth_headers)
    assert response.status_code == 200
```

### Test Credit Operations

```python
def test_credits(self, integration_client, auth_headers):
    # Trigger trial credits
    integration_client.get("/api/auth/me", headers=auth_headers)

    # Check balance
    response = integration_client.get("/api/billing/balance", headers=auth_headers)
    assert response.json()["balance"] == 5
```

### Test Insufficient Credits

```python
def test_insufficient_credits(self, integration_client, auth_headers, supabase_admin, test_user):
    # Set credits to 0
    supabase_admin.table("credits").update({"balance": 0}).eq("user_id", test_user["id"]).execute()

    response = integration_client.post(f"/api/photos/{photo_id}/score", headers=auth_headers)
    assert response.status_code == 402
```

### Test File Upload

```python
def test_upload(self, integration_client, auth_headers, sample_jpeg_bytes, cleanup_storage):
    from io import BytesIO

    response = integration_client.post(
        "/api/photos/upload",
        headers=auth_headers,
        files={"file": ("test.jpg", BytesIO(sample_jpeg_bytes), "image/jpeg")},
    )
    assert response.status_code == 200
    assert "id" in response.json()
```

---

## API Endpoints Reference

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/me` | GET | Yes | Get user info, grants trial credits |
| `/api/billing/balance` | GET | Yes | Get credit balance |
| `/api/billing/transactions` | GET | Yes | Get transaction history |
| `/api/photos` | GET | Yes | List photos |
| `/api/photos/upload` | POST | Yes | Upload photo |
| `/api/photos/{id}` | GET | Yes | Get photo details |
| `/api/photos/{id}/score` | POST | Yes | Score photo (costs 1 credit) |
| `/api/photos/{id}/regenerate` | POST | Yes | Regenerate explanation |
| `/api/photos/{id}` | DELETE | Yes | Delete photo |

---

## Full Documentation

See `packages/api/TESTING.md` for complete testing guide.
