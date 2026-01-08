# ADR-004: Template-Based Deterministic Explanations

## Status

Accepted

## Date

2024-01-01

## Context

After scoring, users want to understand **why** a photo received its score. Options:
1. Call an LLM to generate a natural language explanation
2. Use deterministic templates based on scored attributes

LLM explanations are more natural but add latency and cost. Templates are instant and predictable.

## Decision

Use **deterministic template-based explanations** for score justification.

### Implementation

The `ExplanationGenerator` class in `photo_score/scoring/explanations.py`:

1. **Tier Classification**: Map scores to human-readable tiers
   ```python
   def get_tier(score: float) -> str:
       if score < 0.3: return "Flawed"
       if score < 0.5: return "Tourist"
       if score < 0.7: return "Competent"
       if score < 0.85: return "Strong"
       return "Excellent"
   ```

2. **Strength/Weakness Identification**:
   - Strengths: attributes >= 0.7
   - Weaknesses: attributes < 0.5

3. **Template Construction**:
   ```
   "This {tier} photo scores {score}/100.
   Strengths: {top attributes with high scores}.
   Areas for improvement: {attributes with low scores}."
   ```

4. **Weight-Aware Explanations**: Include how much each attribute contributed to final score

### Example Output

```
This Strong photo scores 78/100. The composition (0.82) and visual
appeal (0.76) are particular strengths. Technical execution is solid
with good sharpness (0.71). The main area for improvement is subject
strength (0.58), which received 35% of the aesthetic weight.
```

## Consequences

### Positive

- **Instant generation**: No API call, zero latency
- **Deterministic**: Same attributes always produce same explanation
- **Cost-free**: No additional inference cost
- **Transparent**: Users can understand the scoring formula
- **Debuggable**: Easy to trace explanation to attribute values

### Negative

- **Less natural**: Templates feel more mechanical than LLM prose
- **Limited nuance**: Can't capture subtle relationships between attributes
- **Maintenance**: Must update templates when scoring logic changes
- **Repetitive**: Similar photos get similar explanations

### Neutral

- Separate `critique` field exists for LLM-generated improvement suggestions
- Templates can be enhanced over time without API cost impact
- Users can still access raw attribute values for deeper analysis

## Alternatives Considered

### 1. LLM-Generated Explanations
- **Rejected for default**: Adds ~$0.001/image and 1-2s latency
- **Kept as option**: `image_critique` table stores LLM critique separately
- Users who want richer explanations can enable critique generation

### 2. No Explanations (Scores Only)
- **Rejected**: Users consistently asked "why this score?"
- Explanations are essential for trust and learning

### 3. Rule-Based with Conditionals
- **Rejected**: Would become unmaintainable spaghetti
- Templates with substitution are cleaner

### 4. Explanation Caching from LLM
- **Rejected**: Still has first-call latency
- Cache invalidation complex if weights change

## References

- `photo_score/scoring/explanations.py`: ExplanationGenerator class
- `photo_score/scoring/reducer.py`: Contribution tracking for explanations
- `photo_score/storage/models.py`: ScoringResult with explanation field
