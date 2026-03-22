# ADR-012: Explicit Product Modes

## Status

Proposed

## Date

2026-03-22

## Context

PhotoScorer has three distinct processing paths with different privacy and data-handling profiles. Existing documentation and UX copy made blanket claims like "images never leave the device" and "all processing happens locally" that are inaccurate for all three paths — even the most private path (desktop + own OpenRouter key) sends image bytes to OpenRouter for inference. The web upload path stores original photos in Supabase Storage with no disclosure at all.

Inaccurate privacy claims erode user trust when discovered and may create legal liability. We need to name each mode explicitly, document its data flow, and ensure all user-facing copy matches reality.

## Decision

Define three named product modes with explicit data-flow guarantees:

### Mode 1: Desktop + Own API Key

| Aspect | Detail |
|--------|--------|
| **Name** | Private Mode |
| **Where image bytes go** | Sent directly to OpenRouter for inference (triage only today; scoring still routes through the cloud API) |
| **What's persisted in cloud** | Attributes + hashes (local only; cloud sync is planned but not yet implemented) |
| **Original photos stored remotely?** | No |
| **Who holds the API key** | User |

> **Implementation note:** The direct-to-OpenRouter path currently only covers triage (`analyze_grid_local`). Individual photo scoring still requires authentication and uses the cloud inference proxy. Extending Private Mode to scoring is planned.

### Mode 2: Desktop + Cloud Credits

| Aspect | Detail |
|--------|--------|
| **Name** | Credit Mode |
| **Where image bytes go** | Sent to PhotoScorer API, proxied to OpenRouter |
| **What's persisted in cloud** | Attributes + hashes |
| **Original photos stored remotely?** | No — only image bytes transit through the API during inference |
| **Who holds the API key** | PhotoScorer (server-side) |

### Mode 3: Web Upload / Triage

| Aspect | Detail |
|--------|--------|
| **Name** | Web Mode |
| **Where image bytes go** | Uploaded to Supabase Storage, processed server-side |
| **What's persisted in cloud** | Original photos + attributes |
| **Original photos stored remotely?** | Yes — stored to support results; user can delete at any time |
| **Who holds the API key** | PhotoScorer (server-side) |

### Copy Guidelines

All user-facing text must follow these rules:

1. **Never claim** "images never leave the device" — even Private Mode sends bytes to OpenRouter.
2. **Desktop copy** should say photos are "not stored in the cloud" and note that "image data is sent to AI providers for analysis."
3. **Web upload copy** must disclose that photos are uploaded to cloud servers for processing.
4. **Use mode-specific language** when the context is clear (e.g., Settings panel in the desktop app vs. the Upload page on the webapp).

## Consequences

### Positive

- Users get accurate, transparent information about how their data is handled
- Reduces legal risk from misleading privacy claims
- Provides a clear framework for evaluating privacy impact of future features
- Makes it easy for contributors to write correct copy

### Negative

- Privacy messaging becomes more nuanced (less punchy marketing copy)
- Requires updating existing copy across multiple surfaces

### Neutral

- No code-level architectural changes — this ADR governs documentation and UX copy only
- Future features (e.g., local inference) would be added as a new mode

## Alternatives Considered

### Single unified privacy statement
- **Rejected**: A single statement can't accurately describe three different data flows. The most conservative statement ("photos may be uploaded to the cloud") would alarm desktop-only users, while a permissive statement ("all local") would be false for web users.

### Defer until local inference is available
- **Rejected**: Current claims are already inaccurate. Waiting would extend the period of misleading copy.

## References

- [ARCHITECTURE.md](../../ARCHITECTURE.md) — System architecture and security considerations
- [ADR-005](005-desktop-electron-sidecar.md) — Desktop Electron + Sidecar architecture
- [ADR-006](006-credit-billing-system.md) — Credit billing system
