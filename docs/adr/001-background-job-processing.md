# ADR-001: Background Job Processing Pattern

## Status

Accepted

## Date

2026-01-09

## Context

We need to process long-running tasks like photo scoring and triage in the background. These tasks:
- Take 10-60+ seconds to complete
- Involve multiple API calls to external services (OpenRouter)
- Should not block HTTP request/response cycles
- Must survive server restarts/hibernation
- Need progress tracking for user feedback

### The Problem

We initially implemented triage processing using FastAPI's `BackgroundTasks`:

```python
@router.post("/start")
async def start_triage(..., background_tasks: BackgroundTasks):
    # Create job record
    job = await triage_service.create_job(...)

    # Start background processing
    background_tasks.add_task(run_triage_background, ...)

    return {"job_id": job_id, "status": "processing"}
```

This approach **failed in production** because:

1. **Server Hibernation**: Render's free tier (and similar platforms) hibernates inactive services. When the server hibernates, all in-process background tasks are killed.

2. **No Persistence**: FastAPI's background tasks run in-memory. If the server restarts, crashes, or scales down, pending tasks are lost.

3. **No Recovery**: There's no mechanism to resume interrupted tasks. Jobs get stuck in "processing" state forever.

4. **Single Server**: Background tasks only run on the server that received the request. This doesn't work with horizontal scaling.

## Decision

Use a **database-backed queue with webhook triggers** for all long-running background jobs. The Edge Function acts as a thin webhook handler that calls back to the Render API, keeping all API keys centralized.

### Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  API Server │────▶│  Database   │
│  (webapp)   │     │  (Render)   │     │ (Supabase)  │
└─────────────┘     └─────────────┘     └──────┬──────┘
                           ▲                   │
                           │                   │ Webhook trigger
                           │                   ▼
                           │            ┌─────────────┐
                           │            │    Edge     │
                           └────────────│  Function   │
                             callback   │  (webhook)  │
                                        └─────────────┘
```

### Why Edge Function Calls Back to Render

1. **Single source of secrets**: OpenRouter API key only stored in Render env vars
2. **Simpler deployment**: No need to sync secrets between Supabase and Render
3. **Full Python ecosystem**: Grid generation uses PIL, which isn't available in Deno
4. **Existing code reuse**: `TriageService.run_triage()` already implemented in Python

### Implementation Pattern

1. **Create Job Record**: API creates a job with `status: 'pending'`

2. **Upload Photos**: API uploads photos to storage, creates photo records

3. **Trigger Processing**: API updates job to `status: 'processing', phase: 'grid_generation'`

4. **Database Webhook**: Fires on UPDATE, calls Edge Function

5. **Edge Function**: Validates payload, calls back to Render API:
   ```
   POST /api/triage/{job_id}/process
   X-Service-Role-Key: <supabase-service-key>
   ```

6. **Render API**: Starts background processing with full access to OpenRouter

7. **Client Polling**: Client polls `/api/triage/{job_id}/status` for updates

### Database Schema

```sql
-- Jobs table serves as the queue
CREATE TABLE triage_jobs (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending, processing, completed, failed
    phase TEXT DEFAULT 'uploading', -- uploading, grid_generation, coarse_pass, fine_pass, complete
    -- ... other fields
);

-- Webhook trigger on UPDATE (not INSERT)
CREATE OR REPLACE FUNCTION notify_triage_job_ready()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'processing' AND NEW.phase = 'grid_generation'
       AND (OLD.status != 'processing' OR OLD.phase != 'grid_generation') THEN
        PERFORM pg_notify('triage_job_ready', json_build_object(
            'job_id', NEW.id,
            'user_id', NEW.user_id
        )::text);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Edge Function (Thin Webhook Handler)

```typescript
// supabase/functions/process-triage/index.ts
Deno.serve(async (req) => {
  const payload = await req.json();
  const job = payload.record;

  // Only process jobs transitioning to processing/grid_generation
  if (job.status !== "processing" || job.phase !== "grid_generation") {
    return new Response(JSON.stringify({ message: "Not ready" }));
  }

  // Call back to Render API to do the actual work
  await fetch(`${API_BASE_URL}/api/triage/${job.id}/process`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Service-Role-Key": SUPABASE_SERVICE_ROLE_KEY,
    },
    body: JSON.stringify({
      user_id: job.user_id,
      target: job.target,
      criteria: job.criteria,
      passes: job.passes,
    }),
  });

  return new Response(JSON.stringify({ success: true }));
});
```

## Consequences

### Positive

- **Resilient**: Jobs survive server hibernation, restarts, and crashes
- **Recoverable**: Failed/stuck jobs can be retried by re-triggering the webhook
- **Centralized Secrets**: All API keys stay in Render environment
- **Observable**: Job state is always in the database; easy to monitor and debug
- **Consistent**: Same pattern for all background jobs (scoring, triage, etc.)

### Negative

- **More Complex**: Requires database triggers, webhooks, and Edge Functions
- **Latency**: Small delay between job creation and webhook trigger (~100-500ms)
- **Cost**: Edge Function invocations have costs (though minimal)
- **Still uses BackgroundTasks**: The Render endpoint uses FastAPI BackgroundTasks, but the webhook ensures the task gets re-triggered if the server hibernates

### Neutral

- **Supabase Dependency**: Ties us to Supabase's webhook and Edge Function infrastructure

## Alternatives Considered

### 1. Edge Function Does All Processing
- **Considered**: Edge Function downloads images, generates grids, calls OpenRouter
- **Rejected**: Would require duplicating OpenRouter API key in Supabase secrets

### 2. FastAPI BackgroundTasks Only
- **Rejected**: Doesn't survive server hibernation (our actual failure case)

### 3. Celery/Redis Queue
- **Rejected**: Requires additional infrastructure (Redis server, Celery workers)
- Would add operational complexity

### 4. AWS SQS + Lambda
- **Rejected**: We're already using Supabase; adding AWS would increase complexity
- Good option if we ever move away from Supabase

### 5. Polling-based Worker
- **Considered**: A separate worker process that polls the database
- **Rejected for now**: Webhooks are simpler and already available

## References

- [Supabase Database Webhooks](https://supabase.com/docs/guides/database/webhooks)
- [Supabase Edge Functions](https://supabase.com/docs/guides/functions)
- Migration 010: `migrations/010_triage_jobs.sql`
- Migration 011: `migrations/011_triage_jobs_webhook.sql`
