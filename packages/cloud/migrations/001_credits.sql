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
