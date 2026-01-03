-- Migration: 007_photo_image_hash
-- Description: Add image_hash column to scored_photos for deduplication
-- Created: 2026-01-03

-- Add image_hash column to scored_photos table
ALTER TABLE scored_photos ADD COLUMN IF NOT EXISTS image_hash VARCHAR(64);

-- Create index for efficient duplicate lookups
CREATE INDEX IF NOT EXISTS idx_scored_photos_user_hash
    ON scored_photos(user_id, image_hash);

-- Note: We don't add a UNIQUE constraint because existing duplicates may exist.
-- The application logic handles deduplication on upload.
