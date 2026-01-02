"""Billing router for credit purchases and management."""

import hashlib
import hmac
import json
from datetime import datetime

import httpx
from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel
from supabase import create_client

from ..config import get_settings
from ..dependencies import CurrentUser, SupabaseClient
from ..services.credits import CreditService

router = APIRouter()

# Credit packages available for purchase
CREDIT_PLANS = [
    {"id": "credits_100", "credits": 100, "price_cents": 200, "description": "100 credits"},
    {"id": "credits_500", "credits": 500, "price_cents": 800, "description": "500 credits"},
    {"id": "credits_2000", "credits": 2000, "price_cents": 2500, "description": "2000 credits"},
]


class BalanceResponse(BaseModel):
    """Response for balance endpoint."""

    balance: int
    user_id: str


class PlanResponse(BaseModel):
    """Credit plan information."""

    id: str
    credits: int
    price_cents: int
    description: str


class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""

    plan_id: str
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    """Response with checkout session URL."""

    checkout_url: str
    session_id: str


class TransactionResponse(BaseModel):
    """Transaction record."""

    id: str
    amount: int
    type: str
    stripe_payment_id: str | None
    created_at: datetime


class TransactionsListResponse(BaseModel):
    """List of transactions."""

    transactions: list[TransactionResponse]
    total: int


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(user: CurrentUser, supabase: SupabaseClient):
    """Get current credit balance for the authenticated user."""
    credit_service = CreditService(supabase)
    balance = await credit_service.get_balance(user.id)

    return BalanceResponse(balance=balance, user_id=user.id)


@router.get("/plans", response_model=list[PlanResponse])
async def get_plans():
    """List available credit packages."""
    return [PlanResponse(**plan) for plan in CREDIT_PLANS]


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(request: CheckoutRequest, user: CurrentUser):
    """Create a Stripe checkout session for purchasing credits."""
    settings = get_settings()

    # Find the requested plan
    plan = next((p for p in CREDIT_PLANS if p["id"] == request.plan_id), None)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan_id: {request.plan_id}",
        )

    # Get the Stripe price ID for this plan
    price_id = getattr(settings, f"stripe_price_id_{plan['credits']}", None)
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stripe price not configured for plan: {request.plan_id}",
        )

    # Create Stripe checkout session
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.stripe.com/v1/checkout/sessions",
            auth=(settings.stripe_secret_key, ""),
            data={
                "mode": "payment",
                "payment_method_types[]": "card",
                "line_items[0][price]": price_id,
                "line_items[0][quantity]": 1,
                "success_url": request.success_url,
                "cancel_url": request.cancel_url,
                "client_reference_id": user.id,
                "metadata[user_id]": user.id,
                "metadata[plan_id]": plan["id"],
                "metadata[credits]": str(plan["credits"]),
            },
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Stripe error: {response.text}",
            )

        session = response.json()

    return CheckoutResponse(
        checkout_url=session["url"],
        session_id=session["id"],
    )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
):
    """Handle Stripe webhook events.

    Processes checkout.session.completed to add credits.
    Note: This endpoint is called by Stripe, not authenticated users.
    """
    settings = get_settings()

    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header",
        )

    # Get raw body for signature verification
    body = await request.body()

    # Verify webhook signature
    if not verify_stripe_signature(body, stripe_signature, settings.stripe_webhook_secret):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    # Parse event
    event = json.loads(body)
    event_type = event.get("type")

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]

        # Extract metadata
        user_id = session.get("metadata", {}).get("user_id")
        credits_str = session.get("metadata", {}).get("credits")
        session_id = session.get("id")

        if not user_id or not credits_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing user_id or credits in session metadata",
            )

        credits = int(credits_str)

        # Create Supabase client for database operations
        supabase = create_client(settings.supabase_url, settings.supabase_service_key)

        # Add credits to user account
        credit_service = CreditService(supabase)
        await credit_service.add_credits(user_id, credits, stripe_payment_id=session_id)

    return {"status": "ok"}


@router.get("/transactions", response_model=TransactionsListResponse)
async def get_transactions(
    user: CurrentUser,
    supabase: SupabaseClient,
    limit: int = 50,
    offset: int = 0,
):
    """Get transaction history for the authenticated user."""
    credit_service = CreditService(supabase)
    transactions = await credit_service.get_transactions(user.id, limit=limit, offset=offset)

    return TransactionsListResponse(
        transactions=[TransactionResponse(**t) for t in transactions],
        total=len(transactions),
    )


def verify_stripe_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Stripe webhook signature.

    Uses the simple signature verification method.
    """
    # Parse signature header
    elements = dict(item.split("=") for item in signature.split(","))
    timestamp = elements.get("t")
    expected_sig = elements.get("v1")

    if not timestamp or not expected_sig:
        return False

    # Compute expected signature
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
    computed_sig = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed_sig, expected_sig)
