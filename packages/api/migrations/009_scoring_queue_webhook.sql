-- Migration: 009_scoring_queue_webhook
-- Description: Configure webhook to trigger Edge Function on queue insert
-- Created: 2025-01-04
--
-- NOTE: This migration creates a database webhook to trigger the
-- process-scoring-queue Edge Function when new jobs are added.
--
-- For Supabase hosted:
-- - The webhook is configured in the Supabase Dashboard under Database > Webhooks
-- - The Edge Function URL would be: https://<project>.supabase.co/functions/v1/process-scoring-queue
--
-- For local development:
-- - Use `supabase functions serve` to run the Edge Function locally
-- - Configure cron or manual triggers to process the queue
--
-- The pg_notify trigger created in 008_scoring_queue.sql can be used
-- with pg_listen in a worker process as an alternative to webhooks.

-- Create a helper function to get the Edge Function URL
-- This is configured as a secret/setting in Supabase
CREATE OR REPLACE FUNCTION get_edge_function_url(function_name TEXT)
RETURNS TEXT AS $$
BEGIN
    -- In production, this would return the actual Edge Function URL
    -- For now, return a placeholder that can be configured
    RETURN COALESCE(
        current_setting('app.edge_function_base_url', TRUE),
        'http://localhost:54321/functions/v1'
    ) || '/' || function_name;
END;
$$ LANGUAGE plpgsql;

-- Add comment explaining the webhook setup
COMMENT ON FUNCTION notify_scoring_queue_insert() IS
'Emits pg_notify event when a new scoring job is added.
This can be used by:
1. Supabase Database Webhooks (configure in Dashboard)
2. A pg_listen worker process
3. Polling the queue table

For production, configure a Database Webhook in Supabase Dashboard:
- Table: scoring_queue
- Events: INSERT
- Webhook URL: https://<project>.supabase.co/functions/v1/process-scoring-queue
- HTTP Method: POST
- Headers: Authorization: Bearer <service-role-key>';

-- Alternative: Create a cron job to process the queue periodically
-- This requires pg_cron extension (available on Supabase Pro)
--
-- CREATE EXTENSION IF NOT EXISTS pg_cron;
--
-- SELECT cron.schedule(
--     'process-scoring-queue',
--     '*/1 * * * *',  -- Every minute
--     $$
--     SELECT net.http_post(
--         url := get_edge_function_url('process-scoring-queue'),
--         headers := '{"Content-Type": "application/json"}'::jsonb,
--         body := '{}'::jsonb
--     )
--     $$
-- );
