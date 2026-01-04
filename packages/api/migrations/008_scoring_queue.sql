-- Migration: 008_scoring_queue
-- Description: Add scoring queue table for background processing
-- Created: 2025-01-04

-- Table for queuing photo scoring jobs
CREATE TABLE IF NOT EXISTS scoring_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    photo_id UUID NOT NULL REFERENCES scored_photos(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    priority INT DEFAULT 0,  -- Higher priority processed first
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    retry_count INT DEFAULT 0,

    -- One queue entry per photo
    UNIQUE(photo_id)
);

-- Indexes for efficient queue processing
CREATE INDEX IF NOT EXISTS idx_scoring_queue_status_priority
    ON scoring_queue(status, priority DESC, created_at ASC)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_scoring_queue_user
    ON scoring_queue(user_id);

CREATE INDEX IF NOT EXISTS idx_scoring_queue_photo
    ON scoring_queue(photo_id);

-- RLS policies
ALTER TABLE scoring_queue ENABLE ROW LEVEL SECURITY;

-- Users can view their own queue entries
CREATE POLICY "Users can view own queue entries"
    ON scoring_queue FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own queue entries
CREATE POLICY "Users can insert own queue entries"
    ON scoring_queue FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Service role has full access (for background processing)
CREATE POLICY "Service role full access scoring_queue"
    ON scoring_queue FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- Function to notify when new job is added to queue
CREATE OR REPLACE FUNCTION notify_scoring_queue_insert()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('scoring_queue_insert', json_build_object(
        'id', NEW.id,
        'user_id', NEW.user_id,
        'photo_id', NEW.photo_id
    )::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to call notification function on insert
DROP TRIGGER IF EXISTS scoring_queue_insert_trigger ON scoring_queue;
CREATE TRIGGER scoring_queue_insert_trigger
    AFTER INSERT ON scoring_queue
    FOR EACH ROW
    EXECUTE FUNCTION notify_scoring_queue_insert();
