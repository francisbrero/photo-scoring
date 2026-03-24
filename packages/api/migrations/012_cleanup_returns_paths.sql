-- Migration: Replace cleanup_expired_triage_jobs() with get_expired_triage_jobs()
--
-- The old function directly deleted DB rows but could not delete Supabase Storage
-- files (which requires the Python SDK), creating orphaned files.
--
-- The new function only identifies expired jobs and their storage paths.
-- A Python endpoint handles storage deletion before DB deletion.

-- Drop the old function
DROP FUNCTION IF EXISTS cleanup_expired_triage_jobs();

-- New function: returns expired jobs with their storage paths
-- Uses LEFT JOIN so expired jobs with zero photos are still returned (storage_path = NULL)
CREATE OR REPLACE FUNCTION get_expired_triage_jobs()
RETURNS TABLE(job_id UUID, storage_path TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT tj.id AS job_id, tp.storage_path
    FROM triage_jobs tj
    LEFT JOIN triage_photos tp ON tp.job_id = tj.id
    WHERE tj.expires_at < NOW()
    AND tj.status NOT IN ('processing');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_expired_triage_jobs() IS
    'Returns expired triage jobs with storage paths for Python-driven cleanup. '
    'LEFT JOIN ensures jobs with zero photos are included (storage_path = NULL).';
