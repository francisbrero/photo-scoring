-- Migration: Triage Jobs
-- Adds tables for tracking triage jobs and their associated photos

-- Table for triage job tracking
CREATE TABLE IF NOT EXISTS triage_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Job status
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'uploading', 'processing', 'completed', 'failed', 'cancelled')),

    -- Configuration
    target TEXT NOT NULL DEFAULT '10%',
    criteria TEXT NOT NULL DEFAULT 'standout',
    passes INT NOT NULL DEFAULT 2,

    -- Progress tracking
    phase TEXT DEFAULT 'uploading'
        CHECK (phase IN ('uploading', 'grid_generation', 'coarse_pass', 'fine_pass', 'complete')),
    current_step INT DEFAULT 0,
    total_steps INT DEFAULT 0,

    -- Results
    total_input INT DEFAULT 0,
    pass1_survivors INT DEFAULT 0,
    final_selected INT DEFAULT 0,
    grids_processed INT DEFAULT 0,
    api_calls INT DEFAULT 0,

    -- Billing
    credits_deducted INT DEFAULT 0,

    -- Metadata
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '24 hours')
);

-- Table for tracking individual photos in a triage job
CREATE TABLE IF NOT EXISTS triage_photos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES triage_jobs(id) ON DELETE CASCADE,

    -- Photo info
    original_filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    image_hash TEXT,
    file_size INT,

    -- Grid position (for debugging/auditing)
    grid_index INT,
    grid_coord TEXT,  -- e.g., "A1", "B12"

    -- Selection results
    selected_coarse BOOLEAN DEFAULT FALSE,
    selected_fine BOOLEAN DEFAULT FALSE,
    final_selected BOOLEAN DEFAULT FALSE,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_triage_jobs_user_id ON triage_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_triage_jobs_status ON triage_jobs(status);
CREATE INDEX IF NOT EXISTS idx_triage_jobs_created ON triage_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_triage_jobs_expires ON triage_jobs(expires_at) WHERE status NOT IN ('completed', 'failed', 'cancelled');

CREATE INDEX IF NOT EXISTS idx_triage_photos_job_id ON triage_photos(job_id);
CREATE INDEX IF NOT EXISTS idx_triage_photos_selected ON triage_photos(job_id, final_selected) WHERE final_selected = TRUE;
CREATE INDEX IF NOT EXISTS idx_triage_photos_hash ON triage_photos(image_hash);

-- Enable Row Level Security
ALTER TABLE triage_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE triage_photos ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Users can only access their own triage jobs
CREATE POLICY "Users can view own triage jobs" ON triage_jobs
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own triage jobs" ON triage_jobs
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own triage jobs" ON triage_jobs
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own triage jobs" ON triage_jobs
    FOR DELETE USING (auth.uid() = user_id);

-- RLS Policies: Users can only access photos in their triage jobs
CREATE POLICY "Users can view own triage photos" ON triage_photos
    FOR SELECT USING (
        job_id IN (SELECT id FROM triage_jobs WHERE user_id = auth.uid())
    );

CREATE POLICY "Users can insert own triage photos" ON triage_photos
    FOR INSERT WITH CHECK (
        job_id IN (SELECT id FROM triage_jobs WHERE user_id = auth.uid())
    );

-- Function to clean up expired triage jobs
CREATE OR REPLACE FUNCTION cleanup_expired_triage_jobs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM triage_jobs
        WHERE expires_at < NOW()
        AND status NOT IN ('processing')
        RETURNING id
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Comment on tables
COMMENT ON TABLE triage_jobs IS 'Tracks triage jobs for batch photo filtering';
COMMENT ON TABLE triage_photos IS 'Individual photos within a triage job';
COMMENT ON COLUMN triage_jobs.target IS 'Selection target: percentage (e.g., "10%") or count (e.g., "50")';
COMMENT ON COLUMN triage_jobs.criteria IS 'Selection criteria: "standout", "quality", or custom text';
COMMENT ON COLUMN triage_jobs.phase IS 'Current processing phase for progress tracking';
