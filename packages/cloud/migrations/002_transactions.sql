-- Migration: Create transactions table for credit history tracking
-- Run this in Supabase SQL Editor after 001_credits.sql

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,  -- positive = purchase/refund, negative = usage
    type TEXT NOT NULL CHECK (type IN ('purchase', 'inference', 'refund')),
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
