-- Migration: 004_inference_cache
-- Description: Add cache tables for inference results
-- Created: 2025-01-01

-- Table for caching inference attributes (aesthetic + technical analysis)
CREATE TABLE IF NOT EXISTS inference_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    image_hash VARCHAR(64) NOT NULL,  -- SHA256 hash
    attributes JSONB NOT NULL,  -- Normalized attributes from AI
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint: one result per user+image combination
    UNIQUE(user_id, image_hash)
);

-- Table for caching metadata extraction results
CREATE TABLE IF NOT EXISTS metadata_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    image_hash VARCHAR(64) NOT NULL,
    metadata JSONB NOT NULL,  -- description, location_name, location_country
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, image_hash)
);

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_inference_cache_user_hash
    ON inference_cache(user_id, image_hash);
CREATE INDEX IF NOT EXISTS idx_metadata_cache_user_hash
    ON metadata_cache(user_id, image_hash);

-- RLS policies
ALTER TABLE inference_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE metadata_cache ENABLE ROW LEVEL SECURITY;

-- Users can only access their own cache entries
CREATE POLICY "Users can view own inference cache"
    ON inference_cache FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own inference cache"
    ON inference_cache FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view own metadata cache"
    ON metadata_cache FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own metadata cache"
    ON metadata_cache FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Service role bypass for backend operations
CREATE POLICY "Service role full access inference_cache"
    ON inference_cache FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Service role full access metadata_cache"
    ON metadata_cache FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');
