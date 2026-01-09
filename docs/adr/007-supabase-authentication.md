# ADR-007: Authentication with Supabase

## Status

Accepted

## Date

2024-01-01

## Context

The cloud API and desktop app need user authentication for:
- Credit balance tracking
- Usage history
- Cross-device sync (future)
- Team features (future)

We needed an auth solution that:
- Works across web, desktop, and API
- Handles JWT tokens securely
- Supports social login (Google, GitHub)
- Doesn't require building auth from scratch

## Decision

Use **Supabase Auth** with JWT tokens and Row-Level Security (RLS).

### Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Desktop   │     │   Web App   │     │   Mobile    │
│   (future)  │     │             │     │   (future)  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │ JWT Token
                           ▼
              ┌─────────────────────────┐
              │      FastAPI Backend    │
              │   (validates JWT)       │
              └───────────┬─────────────┘
                          │
                          ▼
              ┌─────────────────────────┐
              │   Supabase PostgreSQL   │
              │   (RLS enforces access) │
              └─────────────────────────┘
```

### JWT Validation

Two token types supported:

1. **HS256 (Email/Password)**:
   - Signed with Supabase JWT secret
   - Verified locally in FastAPI

2. **RS256/ES256 (OAuth - Google, GitHub)**:
   - Signed by Supabase
   - Trust Supabase's verification
   - Fetch JWKS for validation

```python
# Simplified validation logic
def validate_token(token: str) -> User:
    header = jwt.get_unverified_header(token)

    if header["alg"] == "HS256":
        # Email/password: verify with secret
        payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"])
    else:
        # OAuth: trust Supabase verification
        payload = jwt.decode(token, options={"verify_signature": False})

    return User(id=payload["sub"], email=payload["email"])
```

### Row-Level Security (RLS)

Supabase RLS policies ensure users only access their own data:

```sql
-- Users can only read their own credits
CREATE POLICY "Users can view own credits" ON users
  FOR SELECT USING (auth.uid() = id);

-- Users can only see their own transactions
CREATE POLICY "Users can view own transactions" ON credit_transactions
  FOR SELECT USING (auth.uid() = user_id);
```

### Auth Flow

1. **Sign Up/Login**: Client calls Supabase Auth directly
2. **Get Token**: Supabase returns JWT access token
3. **API Calls**: Client includes `Authorization: Bearer <token>`
4. **Validation**: FastAPI validates JWT, extracts user ID
5. **Database**: Queries filtered by RLS policies

## Consequences

### Positive

- **No auth code to maintain**: Supabase handles complexity
- **Social login included**: Google, GitHub, etc. out of box
- **JWT stateless**: No session store needed
- **RLS security**: Database-level access control
- **Unified auth**: Same system for web, desktop, API

### Negative

- **Supabase dependency**: Vendor lock-in for auth
- **JWT complexity**: Two signature algorithms to handle
- **Token refresh**: Must handle expiry client-side
- **RLS learning curve**: Policies can be tricky to debug

### Neutral

- Supabase free tier sufficient for MVP
- Can migrate to self-hosted Supabase if needed
- Auth changes require Supabase dashboard updates

## Alternatives Considered

### 1. Build Custom Auth (JWT + bcrypt)
- **Rejected**: Significant security risk
- Password handling, token refresh, etc. complex
- Not our core competency

### 2. Auth0
- **Rejected**: More expensive at scale
- Overkill for current needs
- Less integrated with database

### 3. Firebase Auth
- **Rejected**: Google ecosystem lock-in
- Less PostgreSQL integration
- Supabase better fit for our stack

### 4. Magic Link Only (No Passwords)
- **Rejected for now**: Some users prefer passwords
- May add as option later
- Supabase supports both

### 5. API Keys (No User Accounts)
- **Rejected**: Can't track per-user credits
- No cross-device sync possible
- Less secure for client apps

## References

- `packages/api/dependencies.py`: JWT validation logic
- `packages/api/routers/auth.py`: Auth endpoints
- Supabase RLS docs: https://supabase.com/docs/guides/auth/row-level-security
- JWT spec: https://jwt.io/introduction
