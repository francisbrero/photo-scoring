# ADR-009: Grid-Based Visual Triage for Large Collections

## Status

Accepted

## Date

2025-01-09

## Context

Users with large photo collections (2000+ photos from a trip) face significant challenges:
- **High cost**: Full scoring at $0.005/image = $10 for 2000 photos
- **Long processing time**: 7 API calls per image
- **Wasted effort**: Most photos in a typical collection are not "keepers"

The typical use case is a traveler returning with thousands of photos who wants to quickly identify the best 10-20% without manually reviewing each one or paying to fully score all of them.

## Decision

Implement a **two-pass grid-based visual triage** system that dramatically reduces API costs by having vision models evaluate composite grid images instead of individual photos.

### Two-Pass Architecture

**Pass 1 - Coarse Selection (20x20 grids)**
1. Generate composite images with 400 photos each arranged in a 20x20 grid
2. Label grid with coordinates (A-T rows, 1-20 columns)
3. Ask vision models to identify photos with "stand-out potential"
4. Use union consensus: keep photo if **either** Qwen or Gemini selects it
5. Models identify best from burst/similar shots (duplicate handling)

**Pass 2 - Fine Refinement (4x4 grids)**
1. Take survivors from Pass 1 (~20% of original)
2. Generate 4x4 grids (16 photos each) for better per-photo visibility
3. Re-evaluate with same criteria
4. Output final selections

### Selection Criteria

User-configurable:
- **Stand-out potential** (default): Photos that catch the eye, memorable moments
- **Overall quality**: Aesthetic + technical estimation
- **Custom prompt**: Free text (e.g., "photos with dramatic lighting")

### Output

Symlinked folder containing only selected photos, preserving originals.

### Cost Analysis

For 2000 photos:

| Pass | Grid Size | Grids | Models | API Calls | Est. Cost |
|------|-----------|-------|--------|-----------|-----------|
| 1 | 20x20 (400/grid) | 5 | 2 | 10 | ~$0.15 |
| 2 | 4x4 (16/grid) | 25* | 2 | 50 | ~$0.25 |
| **Total** | | | | **60** | **~$0.40** |

*Assuming 20% survival rate from Pass 1 = 400 photos

**Comparison**:
- Full scoring: $10.00 (2000 × $0.005)
- Grid triage: $0.40
- **Savings: 96%**

## Consequences

### Positive

- **Dramatic cost reduction**: 96% cheaper than full scoring
- **Fast processing**: Minutes instead of hours for large collections
- **Good enough accuracy**: Visual triage catches obvious winners/losers
- **User control**: Configurable criteria and pass count
- **Non-destructive**: Symlinks preserve original photos

### Negative

- **Lower precision**: ~100px thumbnails in 20x20 grid lose detail
- **Model limitations**: Vision models may miss subtle quality differences
- **Not a replacement**: Users wanting exact scores still need full scoring
- **Coordinate parsing**: Model responses need robust parsing

### Neutral

- Two-pass provides accuracy/cost trade-off users can control
- Can skip Pass 2 (`--passes 1`) for even faster/cheaper results
- Results complement but don't replace full scoring pipeline

## Alternatives Considered

### 1. Embedding-Based Similarity Clustering
- **Rejected**: Requires different model type (CLIP embeddings)
- Adds complexity without clear quality benefit
- Clustering doesn't directly identify "best" photos

### 2. Single Large Grid (50x50)
- **Rejected**: Thumbnails too small for meaningful evaluation
- 2500 photos per grid = ~40px thumbnails at 2048px
- Models struggle with such small images

### 3. Sequential Individual Thumbnails
- **Rejected**: Still requires many API calls
- Grid approach batches evaluation efficiently

### 4. Local Feature Extraction + Heuristics
- **Rejected**: Misses semantic quality (memorable moments, composition)
- Vision models understand "good photo" holistically

### 5. Intersection Consensus (Both Models Must Agree)
- **Rejected**: Too strict, misses good photos
- Union consensus errs on side of keeping potential winners

## Technical Details

### Grid Coordinate System

```
     1   2   3   4   5   6   7   8   9  10  11  12  13  14  15  16  17  18  19  20
   ┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
 A │A1 │A2 │A3 │...│   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │A20│
   ├───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┤
 B │B1 │   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │B20│
   ├───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┤
   │...│   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │...│
   ├───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┤
 T │T1 │   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │T20│
   └───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘
```

### Models Used

Same models as composite scoring for consistency:
- `qwen/qwen-2.5-vl-72b-instruct` (50% weight)
- `google/gemini-2.5-flash-preview` (50% weight)

### Prompt Structure

```
You are reviewing a grid of {rows}x{cols} photos labeled {coord_range}.

Task: Select photos that {criteria}.

Guidelines:
- Target approximately {target}% of photos
- For similar/duplicate photos, select only the best one
- Consider composition, lighting, moment capture, and visual impact

Return ONLY a comma-separated list of coordinates (e.g., A1, B3, C7, T20).
```

## CLI Design

```bash
# Basic usage - select top 10%
photo-score triage -i ./photos -o ./best --top 10%

# Select top 50 photos (absolute count)
photo-score triage -i ./photos -o ./best --top 50

# Custom criteria
photo-score triage -i ./photos -o ./best --top 10% --criteria "landscapes with dramatic skies"

# Single pass (faster, less accurate)
photo-score triage -i ./photos -o ./best --top 10% --passes 1
```

## References

- Issue #72: Grid-based visual triage for large photo collections
- ADR-001: Inference caching strategy (cache grid results)
- ADR-002: Multi-model composite scoring (same models, union consensus)
- `photo_score/triage/`: Implementation module
