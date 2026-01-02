"""Tests for the credit service and billing endpoints."""

from unittest.mock import MagicMock

import pytest

from api.services.credits import CreditService, InsufficientCreditsError


class MockSupabaseTable:
    """Mock for Supabase table operations."""

    def __init__(self, data=None):
        self._data = data or []
        self._filters = {}

    def select(self, *args):
        return self

    def insert(self, data):
        self._data.append(data)
        return self

    def update(self, data):
        self._update_data = data
        return self

    def eq(self, field, value):
        self._filters[field] = value
        return self

    def order(self, field, desc=False):
        return self

    def range(self, start, end):
        return self

    def execute(self):
        result = MagicMock()
        result.data = self._data
        return result


class MockSupabase:
    """Mock Supabase client."""

    def __init__(self):
        self._tables = {}

    def table(self, name):
        if name not in self._tables:
            self._tables[name] = MockSupabaseTable()
        return self._tables[name]

    def set_table_data(self, name, data):
        self._tables[name] = MockSupabaseTable(data)


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    return MockSupabase()


@pytest.fixture
def credit_service(mock_supabase):
    """Create a credit service with mock Supabase."""
    return CreditService(mock_supabase)


class TestCreditService:
    """Tests for CreditService."""

    @pytest.mark.asyncio
    async def test_get_balance_existing_user(self, mock_supabase):
        """Test getting balance for user with existing credits record."""
        mock_supabase.set_table_data("credits", [{"balance": 100}])
        service = CreditService(mock_supabase)

        balance = await service.get_balance("user-123")

        assert balance == 100

    @pytest.mark.asyncio
    async def test_get_balance_new_user(self, mock_supabase):
        """Test getting balance initializes record for new user."""
        mock_supabase.set_table_data("credits", [])
        service = CreditService(mock_supabase)

        balance = await service.get_balance("user-123")

        assert balance == 0

    @pytest.mark.asyncio
    async def test_deduct_credit_success(self, mock_supabase):
        """Test successful credit deduction."""
        mock_supabase.set_table_data("credits", [{"balance": 10}])
        service = CreditService(mock_supabase)

        new_balance = await service.deduct_credit("user-123", amount=1)

        assert new_balance == 9

    @pytest.mark.asyncio
    async def test_deduct_credit_insufficient(self, mock_supabase):
        """Test deduction fails with insufficient credits."""
        mock_supabase.set_table_data("credits", [{"balance": 0}])
        service = CreditService(mock_supabase)

        with pytest.raises(InsufficientCreditsError) as exc_info:
            await service.deduct_credit("user-123", amount=1)

        assert exc_info.value.required == 1
        assert exc_info.value.available == 0

    @pytest.mark.asyncio
    async def test_add_credits(self, mock_supabase):
        """Test adding credits from purchase."""
        mock_supabase.set_table_data("credits", [{"balance": 50}])
        service = CreditService(mock_supabase)

        new_balance = await service.add_credits("user-123", amount=100, stripe_payment_id="cs_123")

        assert new_balance == 150

    @pytest.mark.asyncio
    async def test_refund_credit(self, mock_supabase):
        """Test refunding credits."""
        mock_supabase.set_table_data("credits", [{"balance": 10}])
        service = CreditService(mock_supabase)

        new_balance = await service.refund_credit("user-123", amount=1)

        assert new_balance == 11

    @pytest.mark.asyncio
    async def test_get_transactions(self, mock_supabase):
        """Test getting transaction history."""
        transactions = [
            {"id": "tx-1", "amount": 100, "type": "purchase"},
            {"id": "tx-2", "amount": -1, "type": "inference"},
        ]
        mock_supabase.set_table_data("transactions", transactions)
        service = CreditService(mock_supabase)

        result = await service.get_transactions("user-123")

        assert len(result) == 2
