# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records for the Photo Scorer project.

## What is an ADR?

An Architecture Decision Record captures an important architectural decision made along with its context and consequences. ADRs help us:

- **Remember why** decisions were made
- **Onboard new team members** quickly
- **Avoid re-debating** settled decisions
- **Track evolution** of the architecture over time

## ADR Index

| ADR | Title | Status | Summary |
|-----|-------|--------|---------|
| [001](001-inference-caching-strategy.md) | Inference Caching Strategy | Accepted | "Inference once, score many times" with SQLite cache |
| [002](002-multi-model-composite-scoring.md) | Multi-Model Composite Scoring | Accepted | Weighted consensus across Qwen + Gemini models |
| [003](003-monorepo-shared-core.md) | Monorepo with Shared Core | Accepted | Single `photo_score` package shared across CLI/desktop/cloud |
| [004](004-template-based-explanations.md) | Template-Based Explanations | Accepted | Deterministic explanations without LLM calls |
| [005](005-desktop-electron-sidecar.md) | Desktop Electron + Sidecar | Accepted | Electron UI with Python FastAPI sidecar |
| [006](006-credit-billing-system.md) | Credit Billing System | Accepted | Prepaid credits with optimistic deduction |
| [007](007-supabase-authentication.md) | Supabase Authentication | Accepted | JWT auth with Row-Level Security |
| [008](008-yaml-configuration.md) | YAML Configuration | Accepted | YAML files with Pydantic validation |
| [009](009-grid-triage.md) | Grid-Based Visual Triage | Accepted | Two-pass grid triage for large collections (96% cost reduction) |

## Creating a New ADR

1. Copy `TEMPLATE.md` to `NNN-short-title.md` (use next available number)
2. Fill in all sections
3. Set status to "Proposed"
4. Submit PR for review
5. After approval, change status to "Accepted"

## ADR Lifecycle

```
Proposed → Accepted → [Deprecated | Superseded]
```

- **Proposed**: Under discussion, not yet approved
- **Accepted**: Approved and in effect
- **Deprecated**: No longer recommended, but no replacement
- **Superseded**: Replaced by a newer ADR (link to replacement)

## Key Principles

These ADRs establish several core principles for the project:

1. **Inference Once, Score Many Times** (ADR-001)
   - Cache vision model responses aggressively
   - Re-scoring should be instant and free

2. **Shared Core, Multiple Frontends** (ADR-003)
   - One `photo_score` Python package
   - CLI, desktop, and cloud all use the same scoring logic

3. **Offline-First Desktop** (ADR-005)
   - Desktop app must work without internet
   - Sidecar architecture enables this

4. **Simple Credit Model** (ADR-006)
   - 1 credit = 1 image scored
   - Prepaid, no surprise charges

## Updating ADRs

ADRs should be treated as **immutable** once accepted. If a decision changes:

1. Create a new ADR with the new decision
2. Mark the old ADR as "Superseded by ADR-NNN"
3. Link to the new ADR

This preserves the historical record of why decisions changed.

## Questions?

If you're unsure whether a decision warrants an ADR, ask:

- Is this decision hard to reverse?
- Will future developers wonder "why did we do this?"
- Does this affect multiple parts of the system?

If yes to any, write an ADR.
