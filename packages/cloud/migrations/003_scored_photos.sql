-- Migration: Create scored_photos table for storing photo scoring results
-- Run this in Supabase SQL Editor after 002_transactions.sql

-- Scored photos table
CREATE TABLE IF NOT EXISTS scored_photos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    storage_path TEXT NOT NULL,
    original_filename TEXT,

    -- Scoring results
    final_score NUMERIC,
    aesthetic_score NUMERIC,
    technical_score NUMERIC,

    -- AI-generated content
    description TEXT,
    explanation TEXT,
    improvements TEXT,

    -- Metadata
    scene_type TEXT,
    lighting TEXT,
    subject_position TEXT,
    location_name TEXT,
    location_country TEXT,

    -- Detailed scores and features (JSON for flexibility)
    features_json JSONB,
    model_scores JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure unique storage path per user
    UNIQUE(user_id, storage_path)
);

-- Trigger to update updated_at on changes
CREATE OR REPLACE FUNCTION update_scored_photos_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER scored_photos_updated_at
    BEFORE UPDATE ON scored_photos
    FOR EACH ROW
    EXECUTE FUNCTION update_scored_photos_updated_at();

-- Indexes for efficient queries
CREATE INDEX idx_scored_photos_user ON scored_photos(user_id);
CREATE INDEX idx_scored_photos_user_created ON scored_photos(user_id, created_at DESC);
CREATE INDEX idx_scored_photos_user_score ON scored_photos(user_id, final_score DESC);

-- Row-Level Security
ALTER TABLE scored_photos ENABLE ROW LEVEL SECURITY;

-- Users can view their own photos
CREATE POLICY "Users can view own photos" ON scored_photos
    FOR SELECT USING (auth.uid() = user_id);

-- Users can delete their own photos
CREATE POLICY "Users can delete own photos" ON scored_photos
    FOR DELETE USING (auth.uid() = user_id);

-- Only service role can insert/update (prevents client manipulation)
CREATE POLICY "Service role can manage scored_photos" ON scored_photos
    FOR ALL USING (auth.role() = 'service_role');

-- Comments for documentation
COMMENT ON TABLE scored_photos IS 'Stores scored photo results for each user';
COMMENT ON COLUMN scored_photos.storage_path IS 'Path in Supabase Storage (e.g., photos/user-id/image.jpg)';
COMMENT ON COLUMN scored_photos.final_score IS 'Combined aesthetic + technical score (0-100)';
COMMENT ON COLUMN scored_photos.features_json IS 'Detailed features extracted by vision models';
COMMENT ON COLUMN scored_photos.model_scores IS 'Raw scores from each model (qwen, gpt4o, gemini)';
