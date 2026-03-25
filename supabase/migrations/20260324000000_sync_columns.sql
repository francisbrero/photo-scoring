-- Migration: Add sync-related columns to inference_cache and metadata_cache
-- Supports bi-directional attribute sync between desktop and cloud

-- inference_cache: add updated_at and scored_at
ALTER TABLE inference_cache ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE inference_cache ADD COLUMN IF NOT EXISTS scored_at TIMESTAMPTZ;

-- metadata_cache: add updated_at
ALTER TABLE metadata_cache ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Backfill updated_at from created_at where NULL
UPDATE inference_cache SET updated_at = created_at WHERE updated_at IS NULL;
UPDATE metadata_cache SET updated_at = created_at WHERE updated_at IS NULL;

-- Trigger: auto-set updated_at on UPDATE for inference_cache
CREATE OR REPLACE FUNCTION update_inference_cache_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER inference_cache_updated_at
    BEFORE UPDATE ON inference_cache
    FOR EACH ROW
    EXECUTE FUNCTION update_inference_cache_updated_at();

-- Trigger: auto-set updated_at on UPDATE for metadata_cache
CREATE OR REPLACE FUNCTION update_metadata_cache_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER metadata_cache_updated_at
    BEFORE UPDATE ON metadata_cache
    FOR EACH ROW
    EXECUTE FUNCTION update_metadata_cache_updated_at();

-- Indexes for cursor-based pagination: (user_id, updated_at, id)
CREATE INDEX IF NOT EXISTS idx_inference_cache_sync_cursor
    ON inference_cache(user_id, updated_at, id);
CREATE INDEX IF NOT EXISTS idx_metadata_cache_sync_cursor
    ON metadata_cache(user_id, updated_at, id);

-- RLS: UPDATE policies for both tables (existing policies only cover SELECT/INSERT)
CREATE POLICY "Users can update own inference cache"
    ON inference_cache FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own metadata cache"
    ON metadata_cache FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);
