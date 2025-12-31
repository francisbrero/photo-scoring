---
description: Estimate API costs for scoring photos
argument-hint: <photo-count>
---

# Estimate Costs

Calculate estimated API costs for scoring photos.

## Usage

```
/costs 100
/costs 1000
```

## Pricing

**Current cost: ~$0.005 per image** (7 API calls)

## Cost Table

| Photos | Estimated Cost |
|--------|----------------|
| 10 | $0.05 |
| 50 | $0.25 |
| 100 | $0.50 |
| 500 | $2.50 |
| 1,000 | $5.00 |
| 10,000 | $50.00 |

## Breakdown Per Image

| Step | Model | Cost |
|------|-------|------|
| Feature extraction | Pixtral 12B | ~$0.0003 |
| Aesthetic (x2) | Qwen + Gemini | ~$0.0010 |
| Technical (x2) | Qwen + Gemini | ~$0.0010 |
| Metadata | Pixtral 12B | ~$0.0003 |
| Critique | Gemini 3 Flash | ~$0.0020 |
| **Total** | | **~$0.0046** |

## Check Actual Usage

View real usage at: https://openrouter.ai/activity
