# ADR-001: Inference Once, Score Many Times (Caching Strategy)

## Status

Accepted

## Date

2024-01-01

## Context

Vision model inference is expensive (~$0.005 per image across 7 API calls). Users often want to:
- Re-score photos with different weight configurations
- Recover from interruptions without re-processing
- Work offline after initial scoring
- Avoid re-processing duplicate images (same photo, different filename)

We needed a strategy that minimizes API costs while maximizing flexibility.

## Decision

Implement aggressive SQLite caching with the principle: **"Inference once, score many times."**

### Implementation Details

1. **Cache Location**: `~/.photo_score/cache.db` (per-user local SQLite)

2. **Image Identity**: SHA256 hash of file bytes (not filename)
   - Allows cache hits across copies of the same image
   - Deduplication built-in

3. **What's Cached**:
   - `inference_results`: Raw model responses (image_id, model_name, model_version, raw_response)
   - `normalized_attributes`: Computed attributes [0,1] range (composition, subject_strength, etc.)
   - `image_metadata`: EXIF + vision-extracted data (date, location, description)
   - `image_critique`: AI-generated descriptions and improvement suggestions

4. **Cache Invalidation**: Manual only (no TTL)
   - Model version stored with results
   - Users can clear cache explicitly if needed

5. **Two CLI Commands**:
   - `photo-score run`: Full pipeline (discovery + inference + scoring)
   - `photo-score rescore`: Instant re-scoring from cache (no API calls)

## Consequences

### Positive

- Re-scoring with different configs is instant (0 API calls)
- Interruption recovery: partial results preserved
- Desktop app works fully offline after first scoring
- Duplicate detection saves money
- Survives API outages gracefully

### Negative

- SQLite limits to single machine (no cross-device cache sharing without sync)
- No automatic invalidation when models improve
- Cache can grow large with many images
- SHA256 sensitive to any file modification (metadata changes break cache)

### Neutral

- Requires explicit `rescore` command for users to understand caching
- Cloud sync feature added separately (ADR-TBD) to share attributes across devices

## Alternatives Considered

### 1. No Caching (Always Re-Infer)
- **Rejected**: Too expensive for iteration workflows
- Cost would be prohibitive for users tweaking weights

### 2. Redis/PostgreSQL Cache
- **Rejected**: Adds infrastructure complexity
- SQLite is sufficient for single-user local workloads
- Can evolve to Redis if needed for cloud caching

### 3. Filename-Based Identity
- **Rejected**: Misses duplicate detection
- Users often have copies with different names

### 4. Time-Based Cache Expiry
- **Rejected**: Vision model outputs don't change
- Manual invalidation preferred for user control

## References

- `photo_score/storage/cache.py`: SQLite cache implementation
- `photo_score/cli.py`: `run` and `rescore` commands
- Cost analysis: 7 API calls × ~$0.0007 average = ~$0.005/image
