# ADR 011: Triage Memory Optimization

## Status

Accepted

## Date

2026-01-09

## Context

The triage feature processes large batches of photos (up to 2,000) by:
1. Downloading images from Supabase Storage
2. Generating grid images with thumbnails
3. Sending grids to vision models for analysis

The initial implementation downloaded **all images into memory at once** before processing, causing memory exhaustion on the Render free tier (512MB limit). For 100 photos at 5MB each, this consumed 500MB+ just for raw image bytes, before PIL processing added additional overhead.

### Observed Failures

```
Instance failed: r99w9
Ran out of memory (used over 512MB) while running your code.
```

### Root Cause

```python
# Original implementation - loads ALL images at once
async def _download_images(self, job_id, photos, user_id):
    images = {}
    for photo in photos:
        response = self.supabase.storage.from_("photos").download(storage_path)
        images[photo["id"]] = response  # Accumulates ALL image bytes
    return images
```

## Decision

Refactor the triage service to use **streaming batch processing**:

1. **Process images grid-by-grid** instead of loading all at once
2. **Download only the images needed for the current grid** (max 400 for coarse, 16 for fine)
3. **Create thumbnails immediately** after download
4. **Discard original image bytes** before processing the next batch
5. **Use generators/iterators** where possible to avoid materializing large lists

### Memory Budget

| Component | Before | After |
|-----------|--------|-------|
| Image download | All photos × avg size | Grid batch × avg size |
| For 100 photos @ 5MB | ~500MB | ~25MB (5 photos/chunk) |
| For 400 photos @ 5MB | ~2GB | ~25MB |
| PIL processing | 2× download size | Minimal (one at a time) |

## Implementation

### Phase 1: Batch Download (Implemented)

```python
async def _download_images_batch(self, photos: list[dict]) -> dict[str, bytes]:
    """Download a small batch of images (for one grid)."""
    images = {}
    for photo in photos:
        response = self.supabase.storage.from_("photos").download(photo["storage_path"])
        images[photo["id"]] = response
    return images
```

The `_run_pass` method now downloads images per-grid instead of upfront.

### Phase 2: Thumbnail-Only Storage (Future)

Store only thumbnails in memory after creation:

```python
async def _download_and_thumbnail(self, photo: dict, size: int) -> tuple[str, Image.Image]:
    """Download image and immediately create thumbnail, discarding original."""
    raw_bytes = self.supabase.storage.from_("photos").download(photo["storage_path"])
    thumbnail = self._create_thumbnail(raw_bytes, size)
    # raw_bytes goes out of scope and is garbage collected
    return photo["id"], thumbnail
```

### Phase 3: Client-Side Thumbnails (Future)

Generate thumbnails in the browser before upload:
- Reduces upload size significantly
- Server only downloads small thumbnails
- Requires webapp changes

### Phase 4: Supabase Image Transforms (Future)

Use Supabase's built-in image transformation:

```
https://project.supabase.co/storage/v1/object/public/photos/path/to/image.jpg?width=100&height=100
```

- No download required
- Thumbnails generated on-demand by Supabase
- Requires signed URLs with transform parameters

## Consequences

### Positive

- **Memory usage reduced by 90%+** for large batches
- **Works within Render free tier** (512MB) for typical workloads
- **Scales to 2,000 photos** without memory issues
- **No change to API contract** - same endpoints, same behavior

### Negative

- **Slightly slower** due to sequential grid processing (acceptable tradeoff)
- **More Supabase Storage API calls** (one per image per pass)
- **Cannot parallelize** grid processing without careful memory management

### Neutral

- Code complexity slightly increased
- Future optimizations (Phase 2-4) provide additional headroom if needed

## Alternatives Considered

### 1. Upgrade Render Plan

- Pros: Simple, no code changes
- Cons: Costs $7-25/month, doesn't solve underlying inefficiency
- Decision: Rejected as primary solution, acceptable as fallback

### 2. Move Processing to Serverless

- Pros: Auto-scaling, pay-per-use
- Cons: Cold starts, complexity, vendor lock-in
- Decision: Deferred - consider if batch processing still insufficient

### 3. Client-Side Grid Generation

- Pros: Zero server memory usage
- Cons: Requires significant webapp changes, browser limitations
- Decision: Already implemented for desktop app, consider for webapp later

### 4. Dedicated Worker Service

- Pros: Isolated scaling, can use more memory
- Cons: Additional infrastructure, complexity
- Decision: Deferred - overkill for current scale

## References

- [Render Memory Limits](https://render.com/docs/free#free-web-services)
- [Supabase Image Transforms](https://supabase.com/docs/guides/storage/serving/image-transformations)
- [PIL Memory Management](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.open)
- ADR 009: Grid-Based Triage
