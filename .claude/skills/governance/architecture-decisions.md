---
description: Architecture Decision Records (ADR) - Enforce and maintain architectural decisions
globs:
  - "docs/adr/**/*.md"
  - "photo_score/**/*.py"
  - "packages/**/*"
alwaysApply: true
---

# Architecture Decision Records (ADR) Governance

## Overview

This skill ensures all code changes respect established Architecture Decision Records. It activates automatically on all files to enforce architectural consistency.

## Active ADRs

Before making significant changes, verify alignment with these decisions:

| ADR | Principle | Violation Signals |
|-----|-----------|-------------------|
| [001](docs/adr/001-inference-caching-strategy.md) | Inference once, score many times | Adding API calls in rescore paths, bypassing cache |
| [002](docs/adr/002-multi-model-composite-scoring.md) | Multi-model weighted consensus | Single-model scoring, hardcoded weights |
| [003](docs/adr/003-monorepo-shared-core.md) | Shared `photo_score` core | Duplicating logic in packages/, platform-specific scoring |
| [004](docs/adr/004-template-based-explanations.md) | Template-based explanations | LLM calls for explanations (except critique) |
| [005](docs/adr/005-desktop-electron-sidecar.md) | Electron + Python sidecar | Node.js scoring logic, direct Python GUI |
| [006](docs/adr/006-credit-billing-system.md) | Prepaid credits, optimistic deduction | Post-payment, deduct after success |
| [007](docs/adr/007-supabase-authentication.md) | Supabase JWT + RLS | Custom auth, session-based auth |
| [008](docs/adr/008-yaml-configuration.md) | YAML config with Pydantic | Database configs, env var configs for weights |
| [009](docs/adr/009-grid-triage.md) | Grid-based triage for large collections | Single-pass only, intersection consensus, per-image API calls for triage |

## Enforcement Checklist

When modifying code, ask:

### Caching (ADR-001)
- [ ] Does this add new API calls? Should they be cached?
- [ ] Is the cache being bypassed unnecessarily?
- [ ] Are SHA256 hashes used for image identity?

### Scoring (ADR-002)
- [ ] Are model weights configurable, not hardcoded?
- [ ] Is consensus used for scoring (not single model)?
- [ ] Are expensive models used only where judgment matters?

### Code Sharing (ADR-003)
- [ ] Is new scoring logic in `photo_score/`, not `packages/`?
- [ ] Can CLI, desktop, and cloud all use this code?
- [ ] Am I duplicating logic that exists in the core?

### Explanations (ADR-004)
- [ ] Are explanations generated from templates?
- [ ] Am I avoiding LLM calls for explanations?
- [ ] Is the critique (LLM-generated) separate from explanations?

### Desktop (ADR-005)
- [ ] Does desktop logic stay in the sidecar (Python)?
- [ ] Is the Electron side only handling UI?
- [ ] Can this work offline?

### Billing (ADR-006)
- [ ] Is credit deduction happening BEFORE the API call?
- [ ] Is there a refund path for failures?
- [ ] Is the transaction logged?

### Auth (ADR-007)
- [ ] Am I using Supabase JWT, not custom auth?
- [ ] Are database queries protected by RLS?
- [ ] Is the user ID from the JWT, not user input?

### Config (ADR-008)
- [ ] Are new settings in YAML, not environment variables?
- [ ] Is Pydantic validating the config?
- [ ] Can users override this in their config file?

## When to Create a New ADR

Create a new ADR when:

1. **Reversing a decision**: Want to change something in an existing ADR
2. **New architectural choice**: Making a decision that affects multiple files/systems
3. **Trade-off discussion**: Choosing between multiple valid approaches
4. **Future developers will ask "why?"**: The reasoning isn't obvious from code

### How to Create

```bash
# 1. Copy template
cp docs/adr/TEMPLATE.md docs/adr/009-your-decision.md

# 2. Fill in all sections
# 3. Submit PR with code changes + ADR

# 4. Update this skill if needed
```

## Common Violations to Watch For

### Anti-Pattern: Bypassing Cache
```python
# BAD: Always calling API
result = client.score_image(image_path)

# GOOD: Check cache first
cached = cache.get_attributes(image_id)
if cached:
    return cached
result = client.score_image(image_path)
cache.store(image_id, result)
```

### Anti-Pattern: Platform-Specific Scoring
```python
# BAD: Scoring logic in desktop package
# packages/desktop/sidecar/scoring.py
def compute_score(attrs):
    return attrs.composition * 0.5 + ...

# GOOD: Use shared core
# photo_score/scoring/reducer.py (shared)
from photo_score.scoring.reducer import ScoringReducer
```

### Anti-Pattern: Hardcoded Weights
```python
# BAD: Hardcoded in code
aesthetic_weight = 0.6

# GOOD: From config
aesthetic_weight = config.category_weights.aesthetic
```

### Anti-Pattern: Post-Payment Deduction
```python
# BAD: Deduct after success
result = client.infer(image)
credits.deduct(user_id, 1)  # What if this fails?

# GOOD: Optimistic deduction
credits.deduct(user_id, 1)
try:
    result = client.infer(image)
except Exception:
    credits.refund(user_id, 1)
    raise
```

## Updating ADRs

ADRs are **immutable** once accepted. To change a decision:

1. Create a new ADR explaining the change
2. Mark the old ADR as "Superseded by ADR-NNN"
3. Update this skill's table
4. Update CLAUDE.md if core principles change

## Resources

- [ADR Index](docs/adr/README.md) - Full list of ADRs
- [ADR Template](docs/adr/TEMPLATE.md) - Template for new ADRs
- [CLAUDE.md](CLAUDE.md) - Project overview and principles
