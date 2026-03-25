"""Tests for sync API endpoints."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_select_chain(mock_table, data):
    """Set up mock for .select().eq().eq().execute() chain."""
    chain = mock_table.select.return_value
    chain = chain.eq.return_value.eq.return_value
    chain.execute.return_value = MagicMock(data=data)


def _mock_query_chain(mock_table, data):
    """Set up mock for .select().eq().order().order().limit().execute()."""
    chain = mock_table.select.return_value
    chain = chain.eq.return_value
    chain = chain.order.return_value.order.return_value
    chain = chain.limit.return_value
    chain.execute.return_value = MagicMock(data=data)
    return chain


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    return MagicMock()


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    from api.dependencies import AuthenticatedUser

    return AuthenticatedUser(id="user-123", email="test@example.com")


@pytest.fixture
def client(mock_supabase, mock_user):
    """Create a test client with mocked dependencies."""
    from api.dependencies import get_current_user, get_supabase_client
    from api.main import create_app

    app = create_app()

    app.dependency_overrides[get_supabase_client] = lambda: mock_supabase
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def unauthed_client():
    """Create a test client without auth overrides."""
    from api.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


class TestPushAttributes:
    """Tests for POST /api/sync/attributes."""

    def test_push_requires_auth(self, unauthed_client):
        """Should return 401/403 without auth."""
        response = unauthed_client.post(
            "/api/sync/attributes",
            json={"attributes": [{"image_id": "abc", "attributes": {"composition": 0.5}}]},
        )
        assert response.status_code in (401, 403)

    def test_push_new_insert(self, client, mock_supabase):
        """Should insert when no existing record."""
        _mock_select_chain(mock_supabase.table.return_value, [])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        response = client.post(
            "/api/sync/attributes",
            json={
                "attributes": [
                    {
                        "image_id": "abc123",
                        "attributes": {
                            "composition": 0.8,
                            "sharpness": 0.7,
                        },
                        "scored_at": "2026-03-24T10:00:00+00:00",
                    }
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["synced"] == 1
        assert data["conflicts"] == []

    def test_push_conflict_cloud_wins_tie(self, client, mock_supabase):
        """Cloud wins when scored_at is equal (tie goes to cloud)."""
        scored_at = "2026-03-24T10:00:00+00:00"
        cloud_attrs = {"composition": 0.9}
        cloud_row = {
            "id": "uuid-1",
            "attributes": cloud_attrs,
            "scored_at": scored_at,
        }

        def table_dispatch(table_name):
            mock_table = MagicMock()
            if table_name == "inference_cache":
                _mock_select_chain(mock_table, [cloud_row])
            elif table_name == "metadata_cache":
                _mock_select_chain(mock_table, [])
            return mock_table

        mock_supabase.table.side_effect = table_dispatch

        response = client.post(
            "/api/sync/attributes",
            json={
                "attributes": [
                    {
                        "image_id": "abc123",
                        "attributes": {"composition": 0.5},
                        "scored_at": scored_at,
                    }
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["synced"] == 0
        assert len(data["conflicts"]) == 1
        conflict = data["conflicts"][0]
        assert conflict["reason"] == "cloud_newer_or_equal"
        assert "cloud_record" in conflict
        assert conflict["cloud_record"]["attributes"] == cloud_attrs

    def test_push_update_incoming_newer(self, client, mock_supabase):
        """Should update when incoming scored_at is strictly newer."""
        existing_row = {
            "id": "uuid-1",
            "attributes": {"composition": 0.5},
            "scored_at": "2026-03-24T09:00:00+00:00",
        }

        def table_dispatch(table_name):
            mock_table = MagicMock()
            if table_name == "inference_cache":
                _mock_select_chain(mock_table, [existing_row])
                update_chain = mock_table.update.return_value
                update_chain.eq.return_value.eq.return_value.execute.return_value = MagicMock()
            return mock_table

        mock_supabase.table.side_effect = table_dispatch

        response = client.post(
            "/api/sync/attributes",
            json={
                "attributes": [
                    {
                        "image_id": "abc123",
                        "attributes": {"composition": 0.8},
                        "scored_at": "2026-03-24T10:00:00+00:00",
                    }
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["synced"] == 1
        assert data["conflicts"] == []

    def test_push_metadata_omission_safe(self, client, mock_supabase):
        """Omitting metadata should not erase existing."""
        _mock_select_chain(mock_supabase.table.return_value, [])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        response = client.post(
            "/api/sync/attributes",
            json={
                "attributes": [
                    {
                        "image_id": "no_meta",
                        "attributes": {"composition": 0.5},
                    }
                ]
            },
        )

        assert response.status_code == 200
        assert response.json()["synced"] == 1

    def test_push_empty_body_422(self, client):
        """Empty attributes list should return 422."""
        response = client.post(
            "/api/sync/attributes",
            json={"attributes": []},
        )
        assert response.status_code == 422

    def test_push_over_batch_limit_422(self, client):
        """More than 1000 records should return 422."""
        records = [
            {"image_id": f"img_{i}", "attributes": {"composition": 0.5}} for i in range(1001)
        ]
        response = client.post(
            "/api/sync/attributes",
            json={"attributes": records},
        )
        assert response.status_code == 422

    def test_push_accepts_mixed_type_attributes(self, client, mock_supabase):
        """Attributes dict may contain strings (model_name, image_id)."""
        _mock_select_chain(mock_supabase.table.return_value, [])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        response = client.post(
            "/api/sync/attributes",
            json={
                "attributes": [
                    {
                        "image_id": "abc123",
                        "attributes": {
                            "image_id": "abc123",
                            "composition": 0.8,
                            "subject_strength": 0.7,
                            "visual_appeal": 0.6,
                            "sharpness": 0.9,
                            "exposure_balance": 0.85,
                            "noise_level": 0.75,
                            "model_name": "cloud",
                            "model_version": "v1",
                        },
                        "scored_at": "2026-03-24T10:00:00+00:00",
                    }
                ]
            },
        )

        assert response.status_code == 200
        assert response.json()["synced"] == 1

    def test_push_none_scored_at_loses_to_existing(self, client, mock_supabase):
        """None scored_at should lose to any non-None cloud scored_at."""
        cloud_row = {
            "id": "uuid-1",
            "attributes": {"composition": 0.9},
            "scored_at": "2026-03-24T10:00:00+00:00",
        }

        def table_dispatch(table_name):
            mock_table = MagicMock()
            if table_name == "inference_cache":
                _mock_select_chain(mock_table, [cloud_row])
            elif table_name == "metadata_cache":
                _mock_select_chain(mock_table, [])
            return mock_table

        mock_supabase.table.side_effect = table_dispatch

        response = client.post(
            "/api/sync/attributes",
            json={
                "attributes": [
                    {
                        "image_id": "abc123",
                        "attributes": {"composition": 0.5},
                        "scored_at": None,
                    }
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["synced"] == 0
        assert len(data["conflicts"]) == 1


class TestPullAttributes:
    """Tests for GET /api/sync/attributes."""

    def test_pull_requires_auth(self, unauthed_client):
        """Should return 401/403 without auth."""
        response = unauthed_client.get("/api/sync/attributes")
        assert response.status_code in (401, 403)

    def test_pull_full(self, client, mock_supabase):
        """Should return all records on full pull (no cursor)."""
        mock_table = MagicMock()
        _mock_query_chain(
            mock_table,
            [
                {
                    "id": "uuid-1",
                    "image_hash": "img1",
                    "attributes": {"composition": 0.8},
                    "scored_at": "2026-03-24T10:00:00+00:00",
                    "updated_at": "2026-03-24T10:00:00+00:00",
                }
            ],
        )

        mock_meta = MagicMock()
        meta_chain = mock_meta.select.return_value
        meta_chain = meta_chain.eq.return_value
        meta_chain.in_.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "image_hash": "img1",
                    "metadata": {"description": "A photo"},
                }
            ]
        )

        def table_dispatch(table_name):
            if table_name == "inference_cache":
                return mock_table
            elif table_name == "metadata_cache":
                return mock_meta
            return MagicMock()

        mock_supabase.table.side_effect = table_dispatch

        response = client.get("/api/sync/attributes")

        assert response.status_code == 200
        data = response.json()
        assert len(data["attributes"]) == 1
        assert data["attributes"][0]["image_id"] == "img1"
        assert data["attributes"][0]["metadata"] == {
            "description": "A photo",
        }
        # Even a partial page returns next_cursor for persistence
        assert data["next_cursor"] is not None

    def test_pull_incremental_cursor(self, client, mock_supabase):
        """Should pass cursor params to query."""
        mock_table = MagicMock()
        chain = _mock_query_chain(mock_table, [])
        chain.or_.return_value.execute.return_value = MagicMock(data=[])

        mock_supabase.table.return_value = mock_table

        response = client.get(
            "/api/sync/attributes",
            params={
                "since": "2026-03-24T09:00:00+00:00",
                "after_id": "uuid-1",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["attributes"] == []
        assert data["next_cursor"] is None

    def test_pull_partial_page_has_cursor(self, client, mock_supabase):
        """Partial (final) page should still return next_cursor."""
        mock_table = MagicMock()
        _mock_query_chain(
            mock_table,
            [
                {
                    "id": "uuid-1",
                    "image_hash": "img1",
                    "attributes": {"composition": 0.8},
                    "scored_at": None,
                    "updated_at": "2026-03-24T10:00:00+00:00",
                }
            ],
        )

        mock_supabase.table.return_value = mock_table

        response = client.get("/api/sync/attributes")

        assert response.status_code == 200
        data = response.json()
        assert len(data["attributes"]) == 1
        # Partial page (1 record < default 500 limit) still has cursor
        assert data["next_cursor"] is not None
        assert data["next_cursor"]["since"] == "2026-03-24T10:00:00+00:00"
        assert data["next_cursor"]["after_id"] == "uuid-1"

    def test_pull_empty_result(self, client, mock_supabase):
        """Should return empty list when no records."""
        mock_table = MagicMock()
        _mock_query_chain(mock_table, [])
        mock_supabase.table.return_value = mock_table

        response = client.get("/api/sync/attributes")

        assert response.status_code == 200
        data = response.json()
        assert data["attributes"] == []
        assert data["next_cursor"] is None


class TestSyncStatus:
    """Tests for GET /api/sync/status."""

    def test_status_requires_auth(self, unauthed_client):
        """Should return 401/403 without auth."""
        response = unauthed_client.get("/api/sync/status")
        assert response.status_code in (401, 403)

    def test_status_returns_count_and_last_sync(self, client, mock_supabase):
        """Should return cloud_count and last_sync."""
        mock_count = MagicMock()
        mock_count.select.return_value.eq.return_value.execute.return_value = MagicMock(
            count=42, data=[]
        )

        mock_latest = MagicMock()
        latest_chain = mock_latest.select.return_value
        latest_chain = latest_chain.eq.return_value
        latest_chain = latest_chain.order.return_value
        latest_chain.limit.return_value.execute.return_value = MagicMock(
            data=[{"updated_at": "2026-03-24T10:00:00+00:00"}]
        )

        call_count = 0

        def table_dispatch(table_name):
            nonlocal call_count
            if table_name == "inference_cache":
                call_count += 1
                if call_count == 1:
                    return mock_count
                return mock_latest
            return MagicMock()

        mock_supabase.table.side_effect = table_dispatch

        response = client.get("/api/sync/status")

        assert response.status_code == 200
        data = response.json()
        assert data["cloud_count"] == 42
        assert data["last_sync"] == "2026-03-24T10:00:00+00:00"
