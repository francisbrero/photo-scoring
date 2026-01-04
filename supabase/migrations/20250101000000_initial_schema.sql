-- Migration: Create credits table for user credit balance tracking
-- Run this in Supabase SQL Editor

-- Credits table
CREATE TABLE IF NOT EXISTS credits (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    balance INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger to update updated_at on changes
CREATE OR REPLACE FUNCTION update_credits_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER credits_updated_at
    BEFORE UPDATE ON credits
    FOR EACH ROW
    EXECUTE FUNCTION update_credits_updated_at();

-- Row-Level Security
ALTER TABLE credits ENABLE ROW LEVEL SECURITY;

-- Users can view their own credits
CREATE POLICY "Users can view own credits" ON credits
    FOR SELECT USING (auth.uid() = user_id);

-- Users cannot directly modify credits (handled by service key)
-- This prevents client-side balance manipulation
CREATE POLICY "Service role can manage credits" ON credits
    FOR ALL USING (auth.role() = 'service_role');

-- Index for performance (primary key already indexed)
COMMENT ON TABLE credits IS 'User credit balance for inference API calls';
COMMENT ON COLUMN credits.balance IS 'Current credit balance (1 credit = 1 image inference)';
-- Migration: Create transactions table for credit history tracking
-- Run this in Supabase SQL Editor after 001_credits.sql

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,  -- positive = purchase/refund, negative = usage
    type TEXT NOT NULL CHECK (type IN ('purchase', 'inference', 'refund', 'trial')),
    stripe_payment_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for efficient user transaction queries
CREATE INDEX idx_transactions_user ON transactions(user_id);
CREATE INDEX idx_transactions_user_created ON transactions(user_id, created_at DESC);

-- Row-Level Security
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

-- Users can view their own transactions
CREATE POLICY "Users can view own transactions" ON transactions
    FOR SELECT USING (auth.uid() = user_id);

-- Only service role can insert/update transactions (prevents client manipulation)
CREATE POLICY "Service role can manage transactions" ON transactions
    FOR ALL USING (auth.role() = 'service_role');

-- Comments for documentation
COMMENT ON TABLE transactions IS 'Credit transaction history for audit trail';
COMMENT ON COLUMN transactions.amount IS 'Credit change: positive for purchases/refunds, negative for usage';
COMMENT ON COLUMN transactions.type IS 'Transaction type: purchase (Stripe), inference (API usage), refund';
COMMENT ON COLUMN transactions.stripe_payment_id IS 'Stripe payment/checkout session ID for purchase transactions';
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
