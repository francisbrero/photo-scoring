---
description: API cost reference for photo scoring, model pricing
globs: []
alwaysApply: false
---

# Cost Reference

## Current Cost Per Image

**~$0.005 per image** (7 API calls)

## Cost Breakdown

| Step | Model | Cost/call |
|------|-------|-----------|
| Feature extraction | Pixtral 12B | ~$0.0003 |
| Aesthetic scoring | Qwen 2.5 VL 72B | ~$0.0002 |
| Aesthetic scoring | Gemini 2.5 Flash | ~$0.0008 |
| Technical scoring | Qwen 2.5 VL 72B | ~$0.0002 |
| Technical scoring | Gemini 2.5 Flash | ~$0.0008 |
| Metadata | Pixtral 12B | ~$0.0003 |
| Critique | Gemini 3 Flash | ~$0.0020 |
| **Total** | | **~$0.0046** |

## Batch Cost Estimates

| Photos | Cost |
|--------|------|
| 10 | $0.05 |
| 50 | $0.25 |
| 100 | $0.50 |
| 500 | $2.50 |
| 1,000 | $5.00 |
| 10,000 | $50.00 |

## Model Pricing (OpenRouter)

| Model | Input | Output |
|-------|-------|--------|
| Pixtral 12B | $0.10/M | $0.10/M |
| Qwen 2.5 VL 72B | $0.40/M | $0.40/M |
| Gemini 2.5 Flash | $0.15/M | $0.60/M |
| Gemini 3 Flash | $0.15/M | $0.60/M |
| Claude 3.5 Sonnet | $3.00/M | $15.00/M |
| GPT-4o-mini | $0.15/M | $0.60/M* |

*GPT-4o-mini encodes images as ~37K tokens (vs ~3K for others), making it 10x more expensive in practice.

## Cost Optimization Tips

1. **Use caching** - Results are cached in `~/.photo_score/cache.db`
2. **Batch processing** - Process multiple images to amortize overhead
3. **Use cheaper models for simple tasks** - Pixtral for metadata, premium models for scoring
4. **Consider hybrid mode** (future) - Local pre-filter + VLM critique

## Monitor Usage

Check actual usage at: https://openrouter.ai/activity

## Historical Notes

- Dec 2024: Removed GPT-4o-mini, reduced cost from ~$0.015 to ~$0.005 (73% savings)
- Dec 2024: Added Gemini 3 Flash for critiques, small cost increase but better quality
