# ADR-014: Picture Storage Strategy

## Status

Accepted

## Date

2026-03-23

## Context

Issue #7 asks us to evaluate and document the photo storage strategy. The project already uses **Supabase Storage** for web-mode photo uploads (triage workflow), with RLS policies, signed URLs, and 24-hour triage job expiration. However, the decision was never formally documented, and several gaps exist:

1. No cost analysis at scale
2. No documented retention policy
3. The automated `cleanup_expired_triage_jobs()` SQL function deletes DB records but leaves **orphaned files** in Supabase Storage (storage deletion requires the Python SDK, not SQL)
4. No formal evaluation of thumbnails/resizing strategy
5. Privacy/security posture undocumented

This ADR formalizes the existing choice and addresses all five evaluation areas from Issue #7.

## Decision

### Storage Provider: Supabase Storage

Continue using Supabase Storage (S3-compatible, integrated with Supabase Auth/RLS). Photos are uploaded via the API server using the service role key, stored under user-scoped paths (`{user_id}/{job_id}/{filename}`), and served via signed URLs.

### Cost Analysis

Supabase Pro plan ($25/mo) includes 100GB storage and 250GB egress. Overage: $0.021/GB storage, $0.09/GB egress.

| Scale | Storage (5MB avg) | Monthly storage overage |
|-------|-------------------|------------------------|
| 1,000 images | 5 GB | $0 (within 100GB) |
| 10,000 images | 50 GB | $0 (within 100GB) |
| 100,000 images | 500 GB | ~$8.40/mo |

**Key insight**: With 24-hour triage expiry, only photos that proceed to scoring persist long-term. A typical triage job selects ~10% of uploads, so steady-state storage is ~10% of peak. At 100K images uploaded, only ~10K (50GB) would persist — well within the included 100GB.

### Retention Policy

- **Triage photos**: Auto-expire with their job at 24 hours (`expires_at` column). Cleanup handled by `POST /internal/cleanup` endpoint (see storage cleanup fix below).
- **Scored photos**: Persist until the user deletes them or their account is deleted (CASCADE from `auth.users`).
- **Storage cleanup**: Python-driven cleanup endpoint replaces the SQL-only `cleanup_expired_triage_jobs()` function, which couldn't delete storage files. The new `get_expired_triage_jobs()` SQL function returns expired jobs with their storage paths; the Python endpoint deletes storage first, then DB rows.

### Thumbnails and Resizing

Two distinct concerns:

1. **Triage processing** (inference artifacts): Temporary PIL thumbnails (100px for coarse pass, 400px for fine pass) are generated in memory during grid analysis and never persisted to storage. These are ephemeral inference artifacts, not user-facing.

2. **User-facing delivery**: Currently serves signed URLs to original files (1-hour expiry) via `create_signed_url()`. No persistent thumbnails or CDN optimization yet.

This is acceptable for MVP. Future optimization: Supabase image transformation (on-the-fly resizing via URL parameters) or pre-generated thumbnails stored alongside originals.

### Privacy and Security

- **Row Level Security (RLS)**: Storage paths are scoped to `{user_id}/`, enforced by RLS policies on `triage_jobs` and `triage_photos` tables. Users can only access their own jobs/photos.
- **Signed URLs**: 1-hour expiry for download URLs, preventing permanent link sharing.
- **Service role isolation**: Only the API server (service role key) uploads/deletes files. Client never gets direct storage access.
- **Ownership verification**: All API endpoints verify `user_id` matches the authenticated user before returning photo data.
- **Account deletion**: CASCADE delete from `auth.users` removes all `triage_jobs` → `triage_photos` records. Storage cleanup runs via the cleanup endpoint.

### Storage Cleanup Fix

The existing `cleanup_expired_triage_jobs()` SQL function (migration 010) directly deletes DB rows but cannot delete Supabase Storage files (which requires the Python SDK). This creates orphaned files.

**Fix**: Replace with `get_expired_triage_jobs()` that only identifies expired jobs and their storage paths. A new `POST /internal/cleanup` Python endpoint:
1. Calls the SQL function to get expired jobs with storage paths
2. Deletes storage files per job (treating 404/not-found as success)
3. Only deletes DB rows after all storage files for that job are cleaned
4. Skips jobs where storage deletion fails (retried on next run)

This ensures no orphaned files: DB rows (source of truth) are only removed after storage is clean.

## Consequences

### Positive

- Zero additional infrastructure — Supabase Storage is included in the existing Supabase plan
- Integrated auth/RLS eliminates a class of access control bugs
- Cost scales well: 24h expiry keeps storage low; 100K images/month still under $10/mo overage
- Storage cleanup is now reliable — no orphaned files

### Negative

- Vendor lock-in to Supabase Storage API (mitigated by S3 compatibility)
- No CDN edge caching for photo delivery (acceptable for MVP, Supabase CDN available as upgrade)
- No on-the-fly image resizing yet (future optimization)

### Neutral

- Cleanup requires a scheduled cron trigger (e.g., Supabase Edge Function or external cron hitting `/internal/cleanup`)
- Storage paths are an implementation detail; migrating to S3 would require updating paths but not the data model

## Alternatives Considered

### Amazon S3 / Cloudflare R2
More control and potentially lower cost at very high scale. Rejected for MVP: requires managing separate infrastructure, IAM policies, and CORS configuration. Supabase Storage provides equivalent functionality with zero additional ops burden.

### Vercel Blob
Simple API, good DX. Rejected: vendor lock-in to Vercel ecosystem, limited RLS integration, separate billing dimension. We already pay for Supabase.

### User's Own Cloud Storage (Google Drive, iCloud)
Would eliminate our storage costs entirely. Rejected: requires complex OAuth flows per provider, unreliable API quotas, and no control over file lifecycle. The triage workflow needs fast, reliable random access to photos.

### Temporary Storage Only (no persistence)
Store photos only during triage, delete immediately after. Rejected: users need to revisit triage results and optionally proceed to full scoring, which requires the original files.

## References

- Supabase Storage pricing: https://supabase.com/pricing
- Storage upload/delete: `packages/api/api/routers/triage.py` (upload at line ~275, cancel/delete at line ~909)
- Cleanup migration: `packages/api/migrations/012_cleanup_returns_paths.sql`
- RLS policies: `packages/api/migrations/010_triage_jobs.sql`
- Triage processing thumbnails: `packages/api/api/services/triage.py` (PIL image resize in grid generation)
