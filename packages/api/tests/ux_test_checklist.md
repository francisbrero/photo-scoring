# Photo Scoring API - UX Testing Checklist

## Pre-Deployment Tests (Local/Staging)

### 1. API Health & Connectivity
- [ ] `GET /health` returns 200 OK
- [ ] `GET /api/health` returns service status
- [ ] Response time < 500ms

### 2. Authentication Flow
- [ ] Unauthenticated requests return 401
- [ ] Valid JWT token grants access
- [ ] Expired tokens are rejected
- [ ] Invalid tokens return 401

### 3. Photo Upload (`POST /api/photos/upload`)
- [ ] JPEG upload succeeds
- [ ] PNG upload succeeds
- [ ] HEIC upload succeeds (if supported)
- [ ] Large file (>10MB) handling
- [ ] Invalid file type rejected
- [ ] Returns photo ID and storage path

### 4. Photo Scoring (`POST /api/photos/{id}/score`)
- [ ] Scoring completes within 30 seconds
- [ ] Returns all expected fields:
  - [ ] `final_score` (0-100)
  - [ ] `aesthetic_score` (0-1)
  - [ ] `technical_score` (0-1)
  - [ ] `description`
- [ ] Credit is deducted on success
- [ ] Credit is refunded on API failure
- [ ] Insufficient credits returns 402

### 5. Direct Scoring (`POST /api/photos/score-direct`)
- [ ] Base64 image accepted
- [ ] Returns all 6 attributes:
  - [ ] `composition`
  - [ ] `subject_strength`
  - [ ] `visual_appeal`
  - [ ] `sharpness`
  - [ ] `exposure_balance`
  - [ ] `noise_level`
- [ ] Returns critique (explanation + improvements)
- [ ] Caching works (second request is free)
- [ ] `cached: true` on cache hit

### 6. Rescore (`POST /api/photos/rescore`)
- [ ] Works without photo_ids (rescores all)
- [ ] Works with specific photo_ids
- [ ] Custom weights applied correctly
- [ ] `persist: false` doesn't modify DB
- [ ] `persist: true` updates DB
- [ ] No credit charge (free operation)

### 7. Photo Retrieval
- [ ] `GET /api/photos` returns paginated list
- [ ] `GET /api/photos/{id}` returns single photo
- [ ] `GET /api/photos/{id}/image` returns image
- [ ] Sorting works (score, date, name)
- [ ] Filtering works

### 8. Credits System
- [ ] `GET /api/credits/balance` returns correct balance
- [ ] Credit deduction on scoring
- [ ] Credit refund on failure
- [ ] Purchase flow (if applicable)

---

## Post-Deployment Tests (Production/Vercel)

### 1. Infrastructure
- [ ] API responds at production URL
- [ ] SSL certificate valid
- [ ] CORS headers correct
- [ ] Rate limiting works

### 2. Cold Start Performance
- [ ] First request completes < 10s (serverless cold start)
- [ ] Subsequent requests < 2s

### 3. End-to-End Flow
- [ ] Upload → Score → Retrieve workflow
- [ ] Direct score workflow (desktop app use case)
- [ ] Rescore with custom weights workflow

### 4. Error Handling
- [ ] 400 for malformed requests
- [ ] 401 for auth failures
- [ ] 402 for insufficient credits
- [ ] 404 for missing resources
- [ ] 500 errors have useful messages
- [ ] 503 for upstream API failures (retryable)

### 5. Data Integrity
- [ ] Scores persist correctly in database
- [ ] Cache entries created
- [ ] No data leakage between users

---

## Automated Test Commands

```bash
# Run unit tests
uv run pytest packages/api/tests/test_photos.py -v

# Run all API tests
uv run pytest packages/api/tests/ -v

# Test specific endpoint
uv run pytest packages/api/tests/test_photos.py::test_rescore_with_default_weights -v

# With coverage
uv run pytest packages/api/tests/ --cov=api --cov-report=term-missing
```

---

## Browser-Based Tests (Chrome Extension)

When using Claude Code with `--chrome` flag:

```
# Test 1: API Health
Navigate to {API_URL}/health and verify JSON response

# Test 2: OpenAPI Docs
Navigate to {API_URL}/docs and verify Swagger UI loads

# Test 3: Auth Flow
Try accessing /api/photos without auth, verify 401 response

# Test 4: Visual Inspection
Check for console errors on all pages
```

---

## Environment Variables to Verify

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Yes | Service role key |
| `SUPABASE_JWT_SECRET` | Yes | JWT signing secret |
| `OPENROUTER_API_KEY` | Yes | For AI inference |
| `STRIPE_SECRET_KEY` | Yes | For payments |
| `STRIPE_WEBHOOK_SECRET` | Yes | For webhook validation |

---

## Test Data Requirements

- Sample JPEG image (< 5MB)
- Sample PNG image (< 5MB)
- Test user with credits
- Test user without credits (for 402 testing)
