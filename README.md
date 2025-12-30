# Photo Scoring CLI

A CLI tool that analyzes photo collections using multiple vision models (via OpenRouter), scores them on aesthetic and technical quality, and produces ranked CSV output with educational critiques.

## Features

- **Multi-model composite scoring** - Uses Qwen, GPT-4o-mini, and Gemini for weighted consensus
- **Feature extraction** - Pixtral extracts scene type, lighting, composition details
- **Aesthetic scoring** - Composition, subject strength, visual appeal (0-1 scale)
- **Technical scoring** - Sharpness, exposure, noise level (0-1 scale)
- **LLM-powered critiques** - Educational, photography-instructor-style feedback
- **Metadata extraction** - AI-generated descriptions and location detection
- **SQLite caching** - Avoids redundant API calls
- **Web viewer** - Review photos with scores and submit corrections
- **HEIC support** - Handles iPhone photos natively

## Installation

```bash
# Clone the repository
git clone https://github.com/francisbrero/photo-scoring.git
cd photo-scoring

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

## Configuration

Set your OpenRouter API key:

```bash
export OPENROUTER_API_KEY="your-api-key"
```

Or create a `.env` file:

```
OPENROUTER_API_KEY=your-api-key
```

## Usage

### Score Photos

```bash
# Basic usage - run calibration on sample images
python calibrate.py -i /path/to/photos -o scores.csv -n 10

# View results in web interface
python serve_viewer.py --photos /path/to/photos --csv scores.csv
```

Open http://localhost:8080 to:
- View photos sorted by score
- See aesthetic/technical breakdowns
- Read detailed critiques and improvement suggestions
- Adjust scores with sliders
- Export corrections as JSON/CSV

---

## Architecture

### Processing Pipeline

Each image goes through a 9-step pipeline:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           IMAGE PROCESSING PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. FEATURE EXTRACTION (Pixtral 12B)                                        │
│     └─> scene_type, subject_position, lighting, background, etc.            │
│                                                                              │
│  2-4. AESTHETIC SCORING (3 models in parallel)                              │
│     ├─> Qwen 2.5 VL 72B (35% weight)                                        │
│     ├─> GPT-4o-mini (35% weight)                                            │
│     └─> Gemini 2.5 Flash (30% weight)                                       │
│         └─> composition, subject_strength, visual_appeal (0-1 each)         │
│                                                                              │
│  5-7. TECHNICAL SCORING (3 models in parallel)                              │
│     ├─> Qwen 2.5 VL 72B (35% weight)                                        │
│     ├─> GPT-4o-mini (35% weight)                                            │
│     └─> Gemini 2.5 Flash (30% weight)                                       │
│         └─> sharpness, exposure, noise_level (0-1 each)                     │
│                                                                              │
│  8. METADATA EXTRACTION (Pixtral 12B)                                       │
│     └─> description, location_name, location_country                        │
│                                                                              │
│  9. CRITIQUE GENERATION (Gemini 2.5 Flash)                                  │
│     └─> summary, strengths, improvements, key_recommendation                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Score Computation

```
Final Score = (Aesthetic Score × 0.6) + (Technical Score × 0.4) × 100

Where:
  Aesthetic Score = (Composition × 0.4) + (Subject Strength × 0.35) + (Visual Appeal × 0.25)
  Technical Score = (Sharpness × 0.4) + (Exposure × 0.35) + (Noise Level × 0.25)
```

---

## Prompts

All prompts are defined in `photo_score/inference/prompts_v2.py`:

### 1. Feature Extraction Prompt

Extracts structured metadata about the image:

```
Output: {
  scene_type: landscape|portrait|street|architecture|nature|food|event|other
  main_subject: "brief description"
  subject_position: center|rule_of_thirds|off_center|multiple
  background: clean|busy|blurred|contextual
  lighting: natural_soft|natural_harsh|golden_hour|blue_hour|artificial|mixed|low_light
  color_palette: vibrant|muted|monochrome|warm|cool|neutral
  depth_of_field: shallow|medium|deep
  time_of_day: dawn|morning|midday|afternoon|golden_hour|dusk|night|unknown
  technical_issues: [blur, noise, overexposed, underexposed, tilted, none]
  ...
}
```

### 2. Aesthetic Scoring Prompt

Rates visual/artistic qualities with harsh calibration:

```
Calibration:
- 0.8-1.0: Exceptional, portfolio-worthy
- 0.6-0.7: Strong, intentional photography
- 0.4-0.5: Average, "camera did its job"
- 0.2-0.3: Below average, tourist snapshot
- 0.0-0.1: Poor, no aesthetic merit

Output: {
  composition: 0.0-1.0,
  subject_strength: 0.0-1.0,
  visual_appeal: 0.0-1.0,
  reasoning: "one sentence"
}
```

### 3. Technical Scoring Prompt

Rates camera work and execution:

```
Output: {
  sharpness: 0.0-1.0,
  exposure: 0.0-1.0,
  noise_level: 0.0-1.0 (1.0 = clean, no noise),
  reasoning: "one sentence"
}
```

### 4. Metadata Prompt

Extracts description and location:

```
Output: {
  description: "1-2 sentence description",
  location_name: "specific place or null",
  location_country: "country or null"
}
```

### 5. Critique Prompt

Generates educational feedback as a photography instructor:

```
Input context:
- All extracted features (scene_type, lighting, etc.)
- All computed scores (composition, sharpness, etc.)
- Final score

Output: {
  summary: "2-3 sentences: overall assessment",
  working_well: [
    "specific strength with WHY it works",
    "another strength"
  ],
  could_improve: [
    "specific issue with concrete suggestion",
    "another improvement with actionable advice"
  ],
  key_recommendation: "single most impactful change"
}
```

---

## Scoring System

### Score Tiers

| Score | Tier | Description |
|-------|------|-------------|
| 85-100 | Excellent | Portfolio-worthy, exceptional |
| 70-84 | Strong | Intentional, well-executed |
| 50-69 | Competent | Solid, "camera did its job" |
| 30-49 | Tourist | Below average snapshot |
| 0-29 | Flawed | Technical issues, poor composition |

### Why Multi-Model?

Using 3 models for scoring provides:
- **Robustness** - Reduces impact of any single model's biases
- **Consensus** - Weighted average smooths outlier scores
- **Calibration** - Different models catch different issues

---

## Model Configuration

| Task | Model | Weight | Cost/M tokens |
|------|-------|--------|---------------|
| Feature Extraction | Pixtral 12B | - | $0.10 |
| Aesthetic Scoring | Qwen 2.5 VL 72B | 35% | $0.07 |
| Aesthetic Scoring | GPT-4o-mini | 35% | $0.15 |
| Aesthetic Scoring | Gemini 2.5 Flash | 30% | $0.30 |
| Technical Scoring | Qwen 2.5 VL 72B | 35% | $0.07 |
| Technical Scoring | GPT-4o-mini | 35% | $0.15 |
| Technical Scoring | Gemini 2.5 Flash | 30% | $0.30 |
| Metadata | Pixtral 12B | - | $0.10 |
| Critique | Gemini 2.5 Flash | - | $0.30 |

**Cost per image:** ~$0.015 (9 API calls)

**Batch costs:**
- 100 images: ~$1.50
- 1,000 images: ~$15.00

> **Note:** GPT-4o-mini encodes images as ~37,000 tokens, accounting for ~77% of the cost. Consider replacing with a cheaper vision model if cost is a concern.

---

## Project Structure

```
photo-scoring/
├── calibrate.py               # Main calibration script
├── serve_viewer.py            # Web viewer server
├── photo_score/
│   ├── inference/
│   │   ├── client.py          # OpenRouter API client
│   │   ├── prompts_v2.py      # All prompt templates ⭐
│   │   └── schemas.py         # Pydantic response models
│   ├── scoring/
│   │   ├── composite.py       # Multi-model scoring engine ⭐
│   │   ├── reducer.py         # Score computation
│   │   └── explanations.py    # (legacy) Score explanations
│   ├── storage/
│   │   ├── cache.py           # SQLite caching
│   │   └── models.py          # Data models
│   ├── ingestion/
│   │   ├── discover.py        # Image discovery
│   │   └── metadata.py        # EXIF extraction
│   └── output/
│       └── csv_writer.py      # CSV output
├── configs/
│   └── default.yaml           # Scoring configuration
└── tests/
    └── test_*.py              # Test suite
```

### Key Files

| File | Purpose |
|------|---------|
| `prompts_v2.py` | All prompt templates - edit here to change scoring behavior |
| `composite.py` | Orchestrates the 9-step pipeline, computes weighted scores |
| `client.py` | Handles API calls, image encoding, JSON parsing, retries |
| `calibrate.py` | CLI entry point for batch processing |
| `serve_viewer.py` | Web UI for reviewing results |

---

## Output Format

The CSV output includes:

| Column | Description |
|--------|-------------|
| `image_path` | Filename |
| `final_score` | 0-100 composite score |
| `aesthetic_score` | 0-1 weighted aesthetic |
| `technical_score` | 0-1 weighted technical |
| `composition` | 0-1 composition score |
| `subject_strength` | 0-1 subject score |
| `visual_appeal` | 0-1 appeal score |
| `sharpness` | 0-1 sharpness score |
| `exposure` | 0-1 exposure score |
| `noise_level` | 0-1 noise score (1=clean) |
| `scene_type` | Detected scene type |
| `lighting` | Detected lighting |
| `description` | AI-generated description |
| `explanation` | Structured critique |
| `improvements` | Actionable suggestions |

---

## Development

```bash
# Run calibration on test images
python calibrate.py -i test_photos/ -o results.csv -n 10

# Start web viewer
python serve_viewer.py --photos test_photos/ --csv results.csv

# Run tests
uv run pytest

# Run specific test
uv run pytest tests/test_reducer.py -v
```

## License

MIT
