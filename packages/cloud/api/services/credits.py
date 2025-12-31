"""Credit service for managing user credit balances and transactions."""

from supabase import Client


class InsufficientCreditsError(Exception):
    """Raised when user doesn't have enough credits for an operation."""

    def __init__(self, required: int, available: int):
        self.required = required
        self.available = available
        super().__init__(f"Insufficient credits: required {required}, available {available}")


class CreditService:
    """Service for credit balance management and transaction logging."""

    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def get_balance(self, user_id: str) -> int:
        """Get user's current credit balance.

        Returns 0 if user has no credits record (initializes one).
        """
        result = self.supabase.table("credits").select("balance").eq("user_id", user_id).execute()

        if result.data:
            return result.data[0].get("balance", 0)

        # Initialize credits record if not exists
        self.supabase.table("credits").insert({"user_id": user_id, "balance": 0}).execute()
        return 0

    async def deduct_credit(self, user_id: str, amount: int = 1) -> int:
        """Deduct credits for inference usage.

        Args:
            user_id: The user's ID
            amount: Number of credits to deduct (default 1)

        Returns:
            New balance after deduction

        Raises:
            InsufficientCreditsError: If user doesn't have enough credits
        """
        current_balance = await self.get_balance(user_id)

        if current_balance < amount:
            raise InsufficientCreditsError(required=amount, available=current_balance)

        new_balance = current_balance - amount

        # Update balance
        self.supabase.table("credits").update({"balance": new_balance}).eq(
            "user_id", user_id
        ).execute()

        # Log transaction
        self.supabase.table("transactions").insert(
            {
                "user_id": user_id,
                "amount": -amount,
                "type": "inference",
            }
        ).execute()

        return new_balance

    async def add_credits(
        self, user_id: str, amount: int, stripe_payment_id: str | None = None
    ) -> int:
        """Add credits from a purchase.

        Args:
            user_id: The user's ID
            amount: Number of credits to add
            stripe_payment_id: Stripe payment/checkout session ID

        Returns:
            New balance after addition
        """
        current_balance = await self.get_balance(user_id)
        new_balance = current_balance + amount

        # Update balance
        self.supabase.table("credits").update({"balance": new_balance}).eq(
            "user_id", user_id
        ).execute()

        # Log transaction
        self.supabase.table("transactions").insert(
            {
                "user_id": user_id,
                "amount": amount,
                "type": "purchase",
                "stripe_payment_id": stripe_payment_id,
            }
        ).execute()

        return new_balance

    async def refund_credit(self, user_id: str, amount: int = 1) -> int:
        """Refund credits (e.g., for failed inference).

        Args:
            user_id: The user's ID
            amount: Number of credits to refund (default 1)

        Returns:
            New balance after refund
        """
        current_balance = await self.get_balance(user_id)
        new_balance = current_balance + amount

        # Update balance
        self.supabase.table("credits").update({"balance": new_balance}).eq(
            "user_id", user_id
        ).execute()

        # Log transaction
        self.supabase.table("transactions").insert(
            {
                "user_id": user_id,
                "amount": amount,
                "type": "refund",
            }
        ).execute()

        return new_balance

    async def get_transactions(self, user_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get user's transaction history.

        Args:
            user_id: The user's ID
            limit: Maximum number of transactions to return
            offset: Number of transactions to skip

        Returns:
            List of transaction records, newest first
        """
        result = (
            self.supabase.table("transactions")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return result.data or []
