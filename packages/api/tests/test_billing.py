"""Tests for the billing endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    """Create test client with mocked settings."""
    # Set required environment variables before importing
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_123")
    monkeypatch.setenv("STRIPE_PRICE_ID_100", "price_100")
    monkeypatch.setenv("STRIPE_PRICE_ID_500", "price_500")
    monkeypatch.setenv("STRIPE_PRICE_ID_2000", "price_2000")

    from api.main import create_app

    app = create_app()
    return TestClient(app)


def test_get_plans(client):
    """Test listing available credit plans."""
    response = client.get("/api/billing/plans")
    assert response.status_code == 200

    plans = response.json()
    assert len(plans) == 3

    # Verify plan structure
    plan_100 = next(p for p in plans if p["id"] == "credits_100")
    assert plan_100["credits"] == 100
    assert plan_100["price_cents"] == 200

    plan_500 = next(p for p in plans if p["id"] == "credits_500")
    assert plan_500["credits"] == 500
    assert plan_500["price_cents"] == 800

    plan_2000 = next(p for p in plans if p["id"] == "credits_2000")
    assert plan_2000["credits"] == 2000
    assert plan_2000["price_cents"] == 2500


def test_get_balance_requires_auth(client):
    """Test that balance endpoint requires authentication."""
    response = client.get("/api/billing/balance")
    assert response.status_code == 401  # No auth header - returns 401 Unauthorized


def test_get_transactions_requires_auth(client):
    """Test that transactions endpoint requires authentication."""
    response = client.get("/api/billing/transactions")
    assert response.status_code == 401  # No auth header - returns 401 Unauthorized


def test_checkout_requires_auth(client):
    """Test that checkout endpoint requires authentication."""
    response = client.post(
        "/api/billing/checkout",
        json={
            "plan_id": "credits_100",
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
        },
    )
    assert response.status_code == 401  # No auth header - returns 401 Unauthorized


def test_webhook_requires_signature(client):
    """Test that webhook endpoint requires Stripe signature."""
    response = client.post("/api/billing/webhook", content=b"{}")
    assert response.status_code == 400
    assert "Missing Stripe-Signature" in response.json()["detail"]


def test_webhook_rejects_invalid_signature(client):
    """Test that webhook rejects invalid signatures."""
    response = client.post(
        "/api/billing/webhook",
        content=b'{"type": "test"}',
        headers={"Stripe-Signature": "t=123,v1=invalid"},
    )
    assert response.status_code == 400
    assert "Invalid signature" in response.json()["detail"]
