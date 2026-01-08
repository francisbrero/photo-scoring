# ADR-002: Multi-Model Composite Scoring

## Status

Accepted

## Date

2024-01-01

## Context

Single vision models have inherent biases and blind spots. Our testing showed:
- Qwen 2.5 VL 72B: Excellent at composition, sometimes misses technical flaws
- Gemini 2.5 Flash: Strong on technical quality, occasionally harsh on artistic choices
- Different models disagree on edge cases

We needed a scoring system that produces consistent, unbiased results while remaining cost-effective.

## Decision

Use **weighted consensus scoring** across multiple models for each scoring dimension.

### Scoring Pipeline

1. **Feature Extraction** (1 call): Mistral Pixtral 12B - $0.0003
2. **Aesthetic Scoring** (2 parallel calls):
   - Qwen 2.5 VL 72B (50% weight)
   - Gemini 2.5 Flash (50% weight)
3. **Technical Scoring** (2 parallel calls):
   - Qwen 2.5 VL 72B (50% weight)
   - Gemini 2.5 Flash (50% weight)
4. **Metadata Extraction** (1 call): Mistral Pixtral 12B - cheap for simple tasks
5. **Critique Generation** (1 call): Gemini 3 Flash Preview - best reasoning

### Model Tiering by Task

| Task | Model | Cost | Rationale |
|------|-------|------|-----------|
| Nuanced scoring | Claude 3.5 Sonnet | $3/M in | Best judgment |
| Simple extraction | Claude 3 Haiku | $0.25/M in | 12x cheaper |
| Feature extraction | Pixtral 12B | $0.0003/call | Bulk work |
| Critique | Gemini 3 Flash | Higher | Best reasoning |

### Consensus Formula

```python
aesthetic_score = (qwen_aesthetic * 0.5) + (gemini_aesthetic * 0.5)
technical_score = (qwen_technical * 0.5) + (gemini_technical * 0.5)
final_score = (aesthetic_score * 0.6) + (technical_score * 0.4)
```

### Total Cost: ~$0.005 per image (7 API calls)

## Consequences

### Positive

- Reduced model bias through consensus
- Quality scores more consistent than single-model
- Can adjust weights if one model proves better
- Parallel calls minimize latency impact
- Cost-effective through tiering

### Negative

- More API calls per image (7 vs 2-3 for single model)
- Debugging harder when models disagree significantly
- Must maintain prompts for multiple models
- OpenRouter dependency for unified API

### Neutral

- Weights are configurable for future tuning
- Can add/remove models without architectural changes
- Calibration command (`calibrate`) exists for model comparison

## Alternatives Considered

### 1. Single Model (GPT-4V or Claude)
- **Rejected**: Higher bias, less robust
- Testing showed 15-20% disagreement on edge cases

### 2. Majority Voting (3+ Models)
- **Rejected**: Diminishing returns vs cost
- Two models provide sufficient consensus

### 3. Ensemble with Learned Weights
- **Rejected**: Requires labeled training data
- Simple averaging works well empirically

### 4. Direct API Calls (No OpenRouter)
- **Rejected**: Multiple API keys to manage
- OpenRouter provides unified interface

## References

- `photo_score/inference/client.py`: OpenRouter client
- `photo_score/inference/prompts.py`: Model-specific prompts
- `calibrate.py`: Benchmark command for model comparison
- OpenRouter pricing: https://openrouter.ai/pricing
