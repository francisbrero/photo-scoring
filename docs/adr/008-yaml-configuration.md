# ADR-008: YAML-Based Scoring Configuration

## Status

Accepted

## Date

2024-01-01

## Context

Users want to customize scoring behavior:
- Adjust weight of aesthetic vs technical attributes
- Change thresholds for score penalties
- Create profiles for different use cases (portraits, landscapes, etc.)

We needed a configuration system that:
- Is human-readable and editable
- Version-controls well (git-friendly)
- Validates against a schema
- Supports multiple named profiles

## Decision

Use **YAML files** for scoring configuration with **Pydantic validation**.

### Configuration Structure

```yaml
# configs/default.yaml
model:
  name: anthropic/claude-3.5-sonnet
  version: "20241022"

weights:
  aesthetic:
    composition: 0.4
    subject_strength: 0.35
    visual_appeal: 0.25
  technical:
    sharpness: 0.4
    exposure_balance: 0.35
    noise_level: 0.25

category_weights:
  aesthetic: 0.6
  technical: 0.4

thresholds:
  sharpness_min: 0.2      # Below this: 50% penalty
  exposure_min: 0.1       # Below this: 30% penalty

output:
  include_raw_attributes: false
  explanation_detail: "standard"  # minimal | standard | verbose
```

### Pydantic Schema

```python
class WeightConfig(BaseModel):
    composition: float = Field(ge=0, le=1)
    subject_strength: float = Field(ge=0, le=1)
    visual_appeal: float = Field(ge=0, le=1)

    @model_validator(mode='after')
    def weights_sum_to_one(self):
        total = self.composition + self.subject_strength + self.visual_appeal
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        return self

class ScoringConfig(BaseModel):
    model: ModelConfig
    weights: WeightsConfig
    category_weights: CategoryWeightsConfig
    thresholds: ThresholdsConfig
    output: OutputConfig = OutputConfig()
```

### Usage Patterns

```bash
# Use default config
photo-score run --input ./photos --output results.csv

# Use custom config
photo-score run --input ./photos --output results.csv --config ./configs/portraits.yaml

# Rescore with different weights (instant, no API calls)
photo-score rescore --input ./photos --output reweighted.csv --config ./configs/high_sharpness.yaml
```

### Config Profiles

```
configs/
├── default.yaml          # Balanced scoring
├── portraits.yaml        # Higher subject_strength weight
├── landscapes.yaml       # Higher composition weight
├── technical.yaml        # Higher technical category weight
└── lenient.yaml          # Lower thresholds
```

## Consequences

### Positive

- **Human-readable**: Easy to understand and modify
- **Version control**: YAML diffs are meaningful
- **Validation**: Pydantic catches errors at load time
- **Multiple profiles**: Easy to maintain variants
- **No database**: No schema migrations needed
- **Portable**: Copy config file to share settings

### Negative

- **Manual editing**: No UI for config changes (yet)
- **Sync needed**: Must distribute config files manually
- **Validation errors**: Can be cryptic for non-developers
- **No hot reload**: Must restart to pick up changes

### Neutral

- Config version can be embedded in output CSV for reproducibility
- Can build config UI in desktop app later
- JSON also valid YAML (forward compatible)

## Alternatives Considered

### 1. Database Configuration
- **Rejected**: Overkill for current needs
- Would require migrations, admin UI
- Harder to version control

### 2. Environment Variables
- **Rejected**: Not structured enough
- Nested configs (weights.aesthetic.composition) awkward
- Hard to maintain multiple profiles

### 3. JSON Configuration
- **Rejected**: Less readable than YAML
- No comments support
- More verbose for nested structures

### 4. TOML Configuration
- **Rejected**: Less familiar to team
- YAML has better ecosystem support
- Nested tables awkward in TOML

### 5. Python Config Files
- **Rejected**: Security risk (code execution)
- Harder for non-developers to edit
- YAML is data, not code

## References

- `photo_score/config/loader.py`: YAML loading with Pydantic
- `photo_score/config/schema.py`: Configuration schemas
- `configs/default.yaml`: Default configuration
- PyYAML docs: https://pyyaml.org/
