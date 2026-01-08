# ADR-006: Credit-Based Billing System

## Status

Accepted

## Date

2024-01-01

## Context

The cloud API incurs real costs (~$0.005/image for inference). We need a billing model that:
- Is simple for users to understand
- Covers API costs with reasonable margin
- Handles failures gracefully (no double-charging)
- Supports volume discounts to encourage usage

## Decision

Implement a **credit-based prepaid billing system** with optimistic deduction.

### Credit Pricing

| Package | Credits | Price | Per-Image | Margin |
|---------|---------|-------|-----------|--------|
| Starter | 100 | $2.00 | $0.020 | 4x |
| Standard | 500 | $8.00 | $0.016 | 3.2x |
| Pro | 2000 | $25.00 | $0.0125 | 2.5x |

Base cost: ~$0.005/image (7 API calls to OpenRouter)

### Credit Flow

```
1. User purchases credits via Stripe Checkout
2. Credits added to user account in Supabase
3. User requests inference via API
4. System checks: credits >= 1?
   - No: Return 402 Payment Required
   - Yes: Continue
5. OPTIMISTIC DEDUCTION: Deduct 1 credit immediately
6. Call OpenRouter for inference
7. On success: Keep deduction, return results
8. On failure: REFUND credit, return error
```

### Database Schema

```sql
-- Credit balance (denormalized for fast reads)
users.credits: integer

-- Transaction log (audit trail)
credit_transactions:
  - id: uuid
  - user_id: uuid
  - amount: integer (positive=add, negative=deduct)
  - type: 'purchase' | 'inference' | 'refund'
  - description: text
  - created_at: timestamp
```

### Optimistic Deduction Rationale

Why deduct **before** the API call?
1. **Prevents race conditions**: Two concurrent requests can't spend the same credit
2. **Simpler error handling**: Refund on failure is cleaner than "try to deduct after"
3. **Audit trail**: Every attempt is logged, successful or not

### Rate Limiting

- 10 requests per 60 seconds per user
- In-memory limiter (production: Redis)
- Prevents accidental credit drain from bugs/loops

## Consequences

### Positive

- **Simple mental model**: 1 credit = 1 image scored
- **Predictable costs**: Users know exactly what they're spending
- **Volume discounts**: Encourages larger purchases
- **Graceful failures**: No charge for failed inferences
- **Clear audit trail**: Every transaction logged

### Negative

- **Prepaid friction**: Users must buy credits before using
- **Credit management**: Users must track balance
- **Refund complexity**: Must handle edge cases (partial failures)
- **No subscription option**: Some users prefer monthly billing

### Neutral

- Stripe handles payment security and PCI compliance
- Can add subscription tier later without changing credit system
- Credits don't expire (user-friendly, but potential liability)

## Alternatives Considered

### 1. Pay-Per-Use (Post-Payment)
- **Rejected**: Higher fraud risk
- Requires credit card on file for every user
- Chargebacks more likely

### 2. Monthly Subscription
- **Rejected for MVP**: More complex to implement
- Users with variable usage prefer pay-as-you-go
- Can add as option later

### 3. Freemium (X Free Images/Month)
- **Rejected**: Abuse potential high
- Difficult to prevent multi-account farming
- May add later with verification

### 4. Per-API-Call Billing (Metered)
- **Rejected**: Too granular for users
- "7 calls per image" confusing
- Credit abstraction is cleaner

## Future Considerations

### HTTP 402 Payment Required
- Exploring 402x micropayment protocol
- Would enable seamless pay-per-request
- Currently using standard 402 status code

### Subscription Tier
- Monthly plan with included credits
- Overage charged at standard rate
- Appeals to predictable-budget users

## References

- `packages/api/routers/billing.py`: Credit management endpoints
- `packages/api/routers/inference.py`: Optimistic deduction logic
- `packages/api/dependencies.py`: Credit check middleware
- Stripe Checkout: https://stripe.com/docs/checkout
