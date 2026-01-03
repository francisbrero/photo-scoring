-- Migration: 006_critique_cache
-- Description: Add critique column to inference_cache table
-- Created: 2026-01-03

-- Add critique column to store explanation, improvements, and description
ALTER TABLE inference_cache
ADD COLUMN IF NOT EXISTS critique JSONB;

-- Comment explaining the structure
COMMENT ON COLUMN inference_cache.critique IS 'Cached critique data: {explanation: string, improvements: string[], description: string}';
