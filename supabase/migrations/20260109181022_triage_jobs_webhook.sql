-- Migration: triage_jobs_webhook
-- Description: Add webhook trigger for triage job processing
-- Created: 2026-01-09
--
-- This migration adds a database trigger that notifies when a triage job
-- is ready for processing (all photos uploaded, status changed to 'processing').

-- Function to notify when a triage job is ready for processing
CREATE OR REPLACE FUNCTION notify_triage_job_ready()
RETURNS TRIGGER AS $$
BEGIN
    -- Only notify when job transitions to 'processing' with 'grid_generation' phase
    -- This indicates all photos are uploaded and job is ready to process
    IF NEW.status = 'processing' AND NEW.phase = 'grid_generation'
       AND (OLD.status != 'processing' OR OLD.phase != 'grid_generation') THEN
        PERFORM pg_notify('triage_job_ready', json_build_object(
            'job_id', NEW.id,
            'user_id', NEW.user_id,
            'total_photos', NEW.total_input,
            'target', NEW.target,
            'criteria', NEW.criteria,
            'passes', NEW.passes
        )::text);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to call notification function on update
DROP TRIGGER IF EXISTS triage_job_ready_trigger ON triage_jobs;
CREATE TRIGGER triage_job_ready_trigger
    AFTER UPDATE ON triage_jobs
    FOR EACH ROW
    EXECUTE FUNCTION notify_triage_job_ready();

-- Also add service role policies for background processing
-- (Service role can update any job for processing)
DROP POLICY IF EXISTS "Service role full access triage_jobs" ON triage_jobs;
DROP POLICY IF EXISTS "Service role full access triage_photos" ON triage_photos;

CREATE POLICY "Service role full access triage_jobs"
    ON triage_jobs FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Service role full access triage_photos"
    ON triage_photos FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- Add comment explaining the webhook setup
COMMENT ON FUNCTION notify_triage_job_ready() IS
'Emits pg_notify event when a triage job is ready for processing.
This is triggered when a job status changes to "processing" with phase "grid_generation".

For production, configure a Database Webhook in Supabase Dashboard:
- Table: triage_jobs
- Events: UPDATE
- Webhook URL: https://jbgkafsmdtotdrrgitzw.supabase.co/functions/v1/process-triage
- HTTP Method: POST
- Headers: Authorization: Bearer <service-role-key>';
