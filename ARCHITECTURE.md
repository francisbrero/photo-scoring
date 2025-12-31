# Architecture Overview

This document describes the architecture for Photo Scoring, supporting both a standalone Electron desktop app and a cloud-hosted service.

## Design Principles

1. **Images never leave the device** - Only SHA256 hashes and extracted attributes sync to cloud
2. **Inference once, score many** - Expensive vision model calls are cached; scoring/recommendations run from cached attributes
3. **Offline-first** - Desktop app works fully offline once images are scored
4. **Cloud-optional** - Cloud sync enables cross-device history, aggregate recommendations, and backup

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Sync strategy** | Background, automatic | Better UX; users don't need to think about it |
| **Offline scoring** | Local inference if powerful machine, else blocked | Balances flexibility with simplicity |
| **Personality recommendations** | On-demand computation | Simpler architecture; avoids background job complexity |
| **Scoring configs** | Private only (for now) | Start simple; library feature planned for future |
| **Auth provider** | Supabase Auth | Unified with PostgreSQL, reduces vendor count |
| **Payment** | Stripe (future: 402x) | Industry standard; 402x for micropayments later |
| **Desktop framework** | Electron | Familiar web tech stack; Python sidecar for core logic |

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Shared Core                                     │
│   photo_score/ (inference, scoring, explanations) - Python package          │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           Electron App (Desktop)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Frontend (React/Vite)                                                       │
│  ├── Photo browser & viewer                                                  │
│  ├── Score dashboard & analytics                                             │
│  ├── Scoring config editor                                                   │
│  └── Recommendations UI (individual + personality insights)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Local Backend (Python sidecar)                                              │
│  ├── Image discovery & thumbnail generation                                  │
│  ├── Inference orchestration                                                 │
│  ├── Local SQLite cache (attributes + metadata)                              │
│  └── Sync service ←→ Cloud                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
              │                                      ▲
              │ Sync attributes/metadata             │ Pull scoring configs
              │ (NOT images)                         │ Pull recommendations
              ▼                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Cloud Backend (Railway)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  API (FastAPI)                                                               │
│  ├── /auth - User accounts, sessions (Supabase Auth)                         │
│  ├── /inference - Proxied OpenRouter calls (deducts credits)                 │
│  ├── /sync - Receive & store user's cached attributes                        │
│  ├── /recommendations - Individual + aggregate "personality" analysis        │
│  ├── /configs - Shareable scoring presets                                    │
│  └── /billing - Credit purchases (Stripe, future: 402x)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  Supabase (PostgreSQL + Auth)                                                │
│  ├── users, sessions (Supabase Auth)                                         │
│  ├── credits, transactions                                                   │
│  ├── cached_attributes (synced from clients)                                 │
│  ├── scoring_configs (user + community presets)                              │
│  └── personality_profiles (aggregate user patterns)                          │
└─────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OpenRouter API                                     │
│                     (Vision models - Qwen, Gemini)                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Inference Flow (Scoring a Photo)

```
User clicks "Score" in Electron app
    │
    ▼
┌─────────────────────────────┐
│ Check local SQLite cache    │
│ (lookup by SHA256 hash)     │
└─────────────────────────────┘
    │
    ├── Cache HIT ──────────────────────────► Use cached attributes
    │                                         (free, instant)
    │
    └── Cache MISS
            │
            ▼
┌─────────────────────────────┐
│ Check connection + credits  │
└─────────────────────────────┘
            │
            ├── Online + has credits ────────► Cloud inference
            │                                  (deducts 1 credit)
            │
            ├── Offline + powerful machine ──► Local inference
            │                                  (free, uses local GPU)
            │
            └── Offline + weak machine ──────► Prompt user to
                                               connect or buy credits
```

### Cloud Inference Path

```
┌─────────────────────────────┐
│ Call cloud /inference       │
│ (requires authentication)   │
└─────────────────────────────┘
            │
            ▼
┌─────────────────────────────┐
│ Cloud backend:              │
│ 1. Verify user credits      │
│ 2. Call OpenRouter API      │
│ 3. Deduct 1 credit          │
│ 4. Return attributes        │
└─────────────────────────────┘
            │
            ▼
┌─────────────────────────────┐
│ Store in local cache        │
│ + background sync to cloud  │
└─────────────────────────────┘
```

### Sync Flow (Attributes to Cloud)

Sync runs **automatically in background** whenever the app has connectivity.

```
Local SQLite                              Supabase PostgreSQL
┌──────────────────┐                     ┌──────────────────┐
│ image_id (SHA256)│                     │ image_id (SHA256)│
│ user_id          │ ───── sync ──────►  │ user_id          │
│ attributes{}     │   (background,      │ attributes{}     │
│ metadata{}       │    automatic)       │ metadata{}       │
│ scored_at        │                     │ synced_at        │
└──────────────────┘                     └──────────────────┘

Benefits of cloud sync:
- Cross-device access to scoring history
- Backup of expensive inference results
- Enables aggregate "personality" recommendations
- Survives app reinstall/device change
```

## Component Details

### Shared Core (`photo_score/`)

The existing Python package, used by both desktop and cloud:

```
photo_score/
├── inference/
│   ├── client.py       # OpenRouter API client
│   ├── prompts.py      # Vision model prompts
│   └── schemas.py      # Pydantic response models
├── scoring/
│   ├── reducer.py      # Weighted score computation
│   └── explanations.py # Template-based explanations
├── storage/
│   ├── cache.py        # SQLite cache interface
│   └── models.py       # Data models
└── recommendations/
    ├── individual.py   # Per-photo suggestions (exists)
    └── personality.py  # Aggregate pattern analysis (new)
```

### Cloud Backend (`packages/cloud/`)

FastAPI application deployed on Railway:

```
packages/cloud/
├── api/
│   ├── main.py              # FastAPI app
│   ├── routers/
│   │   ├── auth.py          # Supabase Auth integration
│   │   ├── inference.py     # Proxied OpenRouter calls
│   │   ├── sync.py          # Attribute sync endpoints
│   │   ├── recommendations.py
│   │   ├── configs.py       # Scoring presets CRUD
│   │   └── billing.py       # Stripe + future 402x
│   ├── services/
│   │   ├── credits.py       # Credit management
│   │   ├── openrouter.py    # API proxy with metering
│   │   └── personality.py   # Aggregate analysis
│   ├── models/
│   │   └── database.py      # SQLAlchemy models
│   └── dependencies.py      # Auth, DB session
├── workers/                  # Background jobs (optional)
│   └── personality_analyzer.py
├── Dockerfile
└── railway.toml
```

### Desktop App (`packages/desktop/`)

Electron app with Python sidecar:

```
packages/desktop/
├── main/                     # Electron main process
│   ├── index.ts
│   ├── sidecar.ts           # Python process management
│   └── ipc.ts               # IPC handlers
├── renderer/                 # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── PhotoBrowser/
│   │   │   ├── ScoreViewer/
│   │   │   ├── ConfigEditor/
│   │   │   └── Recommendations/
│   │   ├── hooks/
│   │   ├── services/
│   │   │   ├── api.ts       # Cloud API client
│   │   │   └── sidecar.ts   # Local Python bridge
│   │   └── stores/
│   └── vite.config.ts
├── sidecar/                  # Python backend
│   ├── server.py            # Local HTTP/WebSocket server
│   ├── handlers/
│   └── pyproject.toml
├── electron-builder.config.js
└── package.json
```

## Database Schema (Supabase)

```sql
-- Users (managed by Supabase Auth)
-- auth.users table is automatic

-- Credit balance and transactions
CREATE TABLE credits (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id),
    balance INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    amount INTEGER NOT NULL,  -- positive = purchase, negative = usage
    type TEXT NOT NULL,       -- 'purchase', 'inference', 'refund'
    stripe_payment_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Synced attributes from desktop clients
CREATE TABLE cached_attributes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    image_id TEXT NOT NULL,   -- SHA256 hash
    attributes JSONB NOT NULL,
    metadata JSONB,           -- EXIF, filename, etc.
    scored_at TIMESTAMPTZ,
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, image_id)
);

-- Scoring configuration presets (private only for now, future: shareable library)
CREATE TABLE scoring_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    name TEXT NOT NULL,
    config JSONB NOT NULL,    -- weights, thresholds
    is_public BOOLEAN DEFAULT FALSE,  -- reserved for future library feature
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Aggregate personality analysis (computed on-demand, cached)
CREATE TABLE personality_profiles (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id),
    profile JSONB NOT NULL,   -- tendencies, strengths, suggestions
    photo_count INTEGER,
    computed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_cached_attributes_user ON cached_attributes(user_id);
CREATE INDEX idx_cached_attributes_scored ON cached_attributes(scored_at);
CREATE INDEX idx_transactions_user ON transactions(user_id);
```

## Credit System

### Pricing Model

```
Cost to serve: ~$0.005 per image (7 OpenRouter API calls)
Suggested pricing:
  - 100 credits  = $2.00  ($0.020/image, 4x margin)
  - 500 credits  = $8.00  ($0.016/image, 3.2x margin)
  - 2000 credits = $25.00 ($0.0125/image, 2.5x margin)
```

### Credit Deduction Flow

```python
async def process_inference(user_id: str, image_hash: str, image_data: bytes):
    # 1. Check balance
    credits = await get_user_credits(user_id)
    if credits.balance < 1:
        raise InsufficientCreditsError()

    # 2. Reserve credit (optimistic)
    await deduct_credit(user_id, amount=1, type='inference')

    try:
        # 3. Call OpenRouter
        attributes = await openrouter_client.analyze(image_data)

        # 4. Store result
        await store_attributes(user_id, image_hash, attributes)

        return attributes
    except Exception as e:
        # 5. Refund on failure
        await add_credit(user_id, amount=1, type='refund')
        raise
```

## Personality Recommendations

Personality analysis is computed **on-demand** when the user requests it (not pre-computed).

### Data Points for Analysis

From synced `cached_attributes`, compute aggregate patterns:

```python
personality_dimensions = {
    # Aesthetic tendencies
    "composition_style": {
        "centered_vs_rule_of_thirds": float,  # -1 to 1
        "minimalist_vs_complex": float,
        "tight_vs_loose_framing": float,
    },

    # Technical patterns
    "exposure_preference": {
        "dark_moody_vs_bright_airy": float,
        "high_contrast_vs_flat": float,
    },

    # Subject matter (from metadata/attributes)
    "subject_distribution": {
        "portraits": float,
        "landscapes": float,
        "street": float,
        "macro": float,
        # ...
    },

    # Scoring patterns
    "score_distribution": {
        "mean": float,
        "std": float,
        "top_10_percent_traits": list[str],  # what makes their best photos
        "bottom_10_percent_traits": list[str],  # common weaknesses
    }
}
```

### Recommendation Types

1. **Strength reinforcement**: "Your portraits consistently score high on subject_strength. This is a clear strength."

2. **Weakness identification**: "Across your collection, exposure_balance tends to be your lowest scoring attribute. Consider..."

3. **Style insights**: "Your photos lean toward high contrast and tight framing. You might enjoy exploring..."

4. **Growth suggestions**: "You haven't shot many landscapes. Trying a new genre could help develop your composition skills."

## API Endpoints

### Authentication (Supabase)

```
POST /auth/signup          # Create account
POST /auth/login           # Get session
POST /auth/logout          # End session
GET  /auth/me              # Current user + credits
```

### Inference

```
POST /inference/analyze
  Body: { image_data: base64, image_hash: sha256 }
  Response: { attributes: {...}, credits_remaining: int }
  Cost: 1 credit
```

### Sync

```
POST /sync/attributes
  Body: { attributes: [{image_id, attributes, metadata, scored_at}, ...] }
  Response: { synced: int }

GET  /sync/attributes
  Query: ?since=timestamp
  Response: { attributes: [...] }
```

### Recommendations

```
GET  /recommendations/personality
  Response: { profile: {...}, suggestions: [...] }

POST /recommendations/refresh
  Response: { status: "computing" }  # triggers background job
```

### Billing

```
GET  /billing/plans           # Available credit packages
POST /billing/checkout        # Create Stripe checkout session
POST /billing/webhook         # Stripe webhook handler
GET  /billing/transactions    # Transaction history
```

## Deployment

### Cloud (Railway)

```yaml
# railway.toml
[build]
builder = "dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 30

[[services]]
name = "api"
```

Environment variables:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `OPENROUTER_API_KEY`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`

### Desktop (Electron)

Build targets:
- macOS: `.dmg` (Apple Silicon + Intel)
- Windows: `.exe` installer
- Linux: `.AppImage`

Python sidecar bundled with PyInstaller.

## Security Considerations

1. **API Key Protection**: OpenRouter key never exposed to clients; all inference proxied through cloud
2. **Image Privacy**: Images never uploaded; only hashes and extracted attributes
3. **Rate Limiting**: Per-user rate limits on inference endpoint
4. **Credit Validation**: Balance checked before every inference call
5. **Row-Level Security**: Supabase RLS policies ensure users only access their own data

## Future Considerations

### 402x Payment Integration

HTTP 402 Payment Required flow for seamless micropayments:

```
Client                         Server
  │                              │
  ├── POST /inference ──────────►│
  │                              │ (insufficient credits)
  │◄── 402 + payment details ────┤
  │                              │
  ├── (402x payment flow) ───────►│
  │                              │
  │◄── 200 + attributes ─────────┤
```

### Potential Expansions

- **Team/organization accounts**: Shared credit pools
- **API access**: Direct API for power users/integrations
- **Preset marketplace**: Community scoring configs
- **Batch processing**: Bulk discount pricing
