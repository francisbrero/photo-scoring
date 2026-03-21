# Roadmap

Last updated: 2026-03-21

## Planning Labels

- `audit-first`: verify whether the issue is stale, partially done, or should be split/closed
- `do-now`: blocks shipping, security, billing, or build stability
- `next`: enables the core platform and v1 product path
- `later`: UX polish, expansion, or optimization after the platform is stable

## Effort Bands

- `S`: 0.5-2 days
- `M`: 3-5 days
- `L`: 1-2 weeks
- `XL`: 2+ weeks

## High-Level Milestones

1. Personal Usability Milestone
2. Soft Launch
3. Production Ready

## Personal Usability Milestone

Goal: make the product reliable and useful for private/self-hosted use without prioritizing Stripe, subscriptions, or broad distribution.

### Audit First

- [ ] #29 Feature: Downloadable desktop app with offline mode (`M`)
- [ ] #3 Support local models for inference (`M`)
- [ ] #8 Add settings page (`S`)

### Do Now

- [x] #85 Fix webapp triage route build break and invalid desktop download CTA (`S`)
- [ ] #89 Repair desktop TypeScript project references so typecheck passes (`M`)
- [ ] #91 Authenticate triage ZIP downloads in the web client (`S`)
- [ ] #87 Extend CI to cover API, webapp, and desktop packages and fail on broken checks (`M`)
- [ ] #93 Define explicit product modes for desktop-private and web-cloud processing (`M`)
- [ ] #7 Define picture storage strategy (`M`)
- [ ] #35 Attribute sync endpoints for desktop-cloud sync (`L`)
- [ ] #38 Local inference fallback for offline/powerful machines (`XL`)
- [ ] #23 Add pyiqa as local scoring backend (`L`)

### Next

- [ ] #92 Generate and share typed API contracts across API, webapp, and desktop (`M`)
- [ ] #98 Version cache keys by model bundle and prompt revision (`M`)
- [ ] #94 Add architecture-level observability for cost, queue health, and retention (`M`)
- [ ] #99 Design a hybrid low-cost funnel for selecting the best photos from large collections (`M`)
- [ ] #95 Add a local pre-filter stage before paid grid triage and scoring (`L`)
- [ ] #25 Add hybrid scoring mode (local pre-filter + VLM critique) (`L`)
- [ ] #12 Add export options beyond CSV (`M`)
- [ ] #24 Add Lightroom XMP sidecar export (`M`)

## Soft Launch

Goal: make the product safe enough for a limited external audience and clarify user-facing policies and product boundaries.

### Audit First

- [ ] #5 Add payment system for credits (`M`)
- [ ] #6 Add free trial with 5 photo credits (`S`)

### Do Now

- [ ] #84 Reject unsigned or forged non-HS256 JWTs in API auth (`L`)
- [ ] #86 Make credit balance mutations atomic across concurrent requests (`L`)
- [ ] #90 Make Stripe webhook processing idempotent and replay-resistant (`M`)
- [ ] #20 Add privacy policy and terms of service (`M`)
- [ ] #42 Configure Stripe products and environment variables (`S`)
- [ ] #19 Create landing page (`M`)
- [ ] #21 Add analytics tracking (`S`)
- [ ] #9 Create picture management features (`L`)

### Next

- [ ] #97 Unify long-running job orchestration around leased, idempotent workers (`XL`)
- [ ] #10 Add rate limiting and error handling UI (`S`)
- [ ] #11 Add batch processing progress indicator (`S`)

## Production Ready

Goal: harden the platform for broader distribution, reduce operational risk, and add higher-level product differentiation.

### Audit First

- [ ] #13 Add comprehensive test coverage (`M`)
- [ ] #14 Add type hints and documentation (`M`)

### Do Now

- [ ] #36 Personality recommendations engine (`XL`)
- [ ] #26 Add score confidence/distribution display (`M`)
- [ ] #17 Add user score calibration (`M`)
- [ ] #16 Add batch actions in viewer (`M`)
- [ ] #15 Add photo comparison mode (`M`)
- [ ] #18 Add before/after editing comparison (`M`)

### Later

- [ ] #38 Local inference fallback for offline/powerful machines (`XL`) if still incomplete after earlier phases
- [ ] #97 Unify long-running job orchestration around leased, idempotent workers (`XL`) if soft launch happens before full worker refactor
- [ ] #13 Add comprehensive test coverage (`M`) as an ongoing track after audit/splitting
- [ ] #14 Add type hints and documentation (`M`) as an ongoing track after audit/splitting

## Suggested Execution Sequence

1. Make the app personally usable without requiring payment or public distribution work.
2. Clarify privacy boundaries and storage behavior while building the private/self-use path.
3. Improve local/offline and low-cost selection flows before scaling outward.
4. Add security, billing hardening, and legal/public-facing launch work for a soft launch.
5. Harden orchestration, observability, testing, and advanced UX for production readiness.
