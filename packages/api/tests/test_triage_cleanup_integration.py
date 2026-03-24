"""Integration tests for triage cleanup endpoint.

Run with: pytest tests/test_triage_cleanup_integration.py -v

Requires local Supabase: supabase start
"""

import uuid
from datetime import UTC, datetime, timedelta

# Import all fixtures from conftest_integration
pytest_plugins = ["tests.conftest_integration"]

from .conftest_integration import (  # noqa: E402
    LOCAL_SUPABASE_SERVICE_KEY,
    requires_supabase,
)


def _create_expired_job(supabase_admin, user_id, *, hours_ago=2):
    """Helper: insert an expired triage job directly via admin client."""
    job_id = str(uuid.uuid4())
    expires_at = (datetime.now(UTC) - timedelta(hours=hours_ago)).isoformat()

    supabase_admin.table("triage_jobs").insert(
        {
            "id": job_id,
            "user_id": user_id,
            "status": "completed",
            "target": "10%",
            "criteria": "standout",
            "passes": 2,
            "expires_at": expires_at,
        }
    ).execute()

    return job_id


def _insert_triage_photo(supabase_admin, job_id, storage_path, filename="test.jpg"):
    """Helper: insert a triage_photos record."""
    photo_id = str(uuid.uuid4())
    supabase_admin.table("triage_photos").insert(
        {
            "id": photo_id,
            "job_id": job_id,
            "original_filename": filename,
            "storage_path": storage_path,
        }
    ).execute()
    return photo_id


@requires_supabase
class TestTriageCleanup:
    """Test the /internal/cleanup endpoint for expired triage jobs."""

    def _cleanup_url(self):
        return f"/api/triage/internal/cleanup?x-internal-key={LOCAL_SUPABASE_SERVICE_KEY}"

    def test_cleanup_expired_job_with_photos(
        self, integration_client, supabase_admin, test_user, sample_jpeg_bytes
    ):
        """Expired job with photos: storage files and DB records should be deleted."""
        user_id = test_user["id"]
        job_id = _create_expired_job(supabase_admin, user_id)

        # Upload a test file to storage
        storage_path = f"{user_id}/{job_id}/photo1.jpg"
        supabase_admin.storage.from_("photos").upload(
            storage_path, sample_jpeg_bytes, {"content-type": "image/jpeg"}
        )

        # Insert photo record
        _insert_triage_photo(supabase_admin, job_id, storage_path, "photo1.jpg")

        # Run cleanup
        response = integration_client.post(self._cleanup_url())
        assert response.status_code == 200

        data = response.json()
        assert data["jobs_cleaned"] >= 1
        assert data["files_deleted"] >= 1

        # Verify DB records are gone
        result = supabase_admin.table("triage_jobs").select("id").eq("id", job_id).execute()
        assert len(result.data) == 0

        result = supabase_admin.table("triage_photos").select("id").eq("job_id", job_id).execute()
        assert len(result.data) == 0

    def test_cleanup_expired_empty_job(self, integration_client, supabase_admin, test_user):
        """Expired job with zero photos: DB record should still be cleaned up."""
        user_id = test_user["id"]
        job_id = _create_expired_job(supabase_admin, user_id)

        # No photos inserted — this is an empty job

        # Run cleanup
        response = integration_client.post(self._cleanup_url())
        assert response.status_code == 200

        data = response.json()
        assert data["jobs_cleaned"] >= 1

        # Verify DB record is gone
        result = supabase_admin.table("triage_jobs").select("id").eq("id", job_id).execute()
        assert len(result.data) == 0

    def test_cleanup_idempotent_missing_storage(
        self, integration_client, supabase_admin, test_user
    ):
        """Storage files already missing: cleanup should still succeed (idempotent)."""
        user_id = test_user["id"]
        job_id = _create_expired_job(supabase_admin, user_id)

        # Insert photo record but do NOT upload file to storage
        storage_path = f"{user_id}/{job_id}/missing.jpg"
        _insert_triage_photo(supabase_admin, job_id, storage_path, "missing.jpg")

        # Run cleanup — should not fail even though storage file doesn't exist
        response = integration_client.post(self._cleanup_url())
        assert response.status_code == 200

        data = response.json()
        assert data["jobs_cleaned"] >= 1

        # Verify DB records are gone
        result = supabase_admin.table("triage_jobs").select("id").eq("id", job_id).execute()
        assert len(result.data) == 0

    def test_cleanup_requires_internal_key(self, integration_client):
        """Cleanup endpoint should reject requests without valid internal key."""
        response = integration_client.post("/api/triage/internal/cleanup")
        assert response.status_code == 401

        response = integration_client.post("/api/triage/internal/cleanup?x-internal-key=wrong-key")
        assert response.status_code == 401

    def test_cleanup_no_expired_jobs(self, integration_client):
        """Cleanup with no expired jobs should return zeros."""
        response = integration_client.post(self._cleanup_url())
        assert response.status_code == 200

        data = response.json()
        assert data["jobs_cleaned"] == 0
        assert data["jobs_skipped"] == 0
        assert data["files_deleted"] == 0
