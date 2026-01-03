---
description: Run UX smoke tests against API (local, staging, or production)
argument-hint: [url] [--token JWT] [--image path]
allowed-tools: Bash(uv run python:*), Bash(curl:*)
---

# UX Smoke Tests

Run automated UX smoke tests against the Photo Scoring API to verify critical user flows work correctly.

## Usage

```
/ux-test                                    # Test local (http://localhost:8000)
/ux-test http://localhost:8000              # Test specific local URL
/ux-test https://api.example.com            # Test production (no auth)
/ux-test https://api.example.com --token JWT  # Test with authentication
/ux-test --image test.jpg                   # Include score-direct test
```

## What It Tests

### Without Authentication
- Health endpoints (`/health`, `/api/health`)
- OpenAPI docs (`/docs`)
- Auth enforcement (401 on protected routes)

### With Authentication (--token)
- Photo listing and pagination
- Photo sorting
- Rescore endpoint (default and custom weights)
- Credits balance
- Error handling (404, 422)
- Score-direct endpoint (if --image provided)

## Commands

### Test Local API
```bash
cd /Users/francis/Documents/MadKudu/photo-scoring/packages/api
uv run python tests/ux_smoke_test.py --url http://localhost:8000 -v
```

### Test Production
```bash
cd /Users/francis/Documents/MadKudu/photo-scoring/packages/api
uv run python tests/ux_smoke_test.py --url $URL --token $TOKEN -v
```

### Test with Image
```bash
cd /Users/francis/Documents/MadKudu/photo-scoring/packages/api
uv run python tests/ux_smoke_test.py --url $URL --token $TOKEN --image /path/to/image.jpg -v
```

## Test Coverage

| Test | Auth Required | Description |
|------|---------------|-------------|
| Health Endpoint | No | Basic `/health` check |
| API Health | No | `/api/health` status |
| OpenAPI Docs | No | Swagger UI loads |
| Auth Required | No | Protected routes return 401 |
| Auth With Token | Yes | Token grants access |
| Credits Balance | Yes | Check credit balance |
| Photos List | Yes | Pagination works |
| Photos Sorting | Yes | Sort options work |
| Rescore Default | Yes | Rescore with defaults |
| Rescore Custom | Yes | Rescore with weights |
| 404 Handling | Yes | Missing resources |
| Validation Error | Yes | Invalid params → 422 |
| Score Direct | Yes + Image | Full scoring pipeline |

## Exit Codes

- `0` - All tests passed
- `1` - One or more tests failed

## Pre-Deployment Checklist

Before deploying to production:

1. Run local tests: `/ux-test http://localhost:8000`
2. Verify staging: `/ux-test https://staging-api.vercel.app --token $STAGING_TOKEN`
3. Check all endpoints respond correctly
4. Review any failures before deploying

## Post-Deployment Verification

After deploying:

1. Run production smoke test: `/ux-test https://api.example.com --token $PROD_TOKEN`
2. Verify cold start times are acceptable
3. Test with a real image if possible
