-- Migration: 005_features_cache
-- Description: Add cache table for scene features (for rich critique generation)
-- Created: 2025-01-01

-- Table for caching extracted scene features
CREATE TABLE IF NOT EXISTS features_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    image_hash VARCHAR(64) NOT NULL,  -- SHA256 hash
    features JSONB NOT NULL,  -- Scene features (scene_type, main_subject, lighting, etc.)
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint: one result per user+image combination
    UNIQUE(user_id, image_hash)
);

-- Index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_features_cache_user_hash
    ON features_cache(user_id, image_hash);

-- RLS policies
ALTER TABLE features_cache ENABLE ROW LEVEL SECURITY;

-- Users can only access their own cache entries
CREATE POLICY "Users can view own features cache"
    ON features_cache FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own features cache"
    ON features_cache FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Service role bypass for backend operations
CREATE POLICY "Service role full access features_cache"
    ON features_cache FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');
