# Photo Scoring CLI

A CLI tool that analyzes photo collections using multiple vision models (via OpenRouter), scores them on aesthetic and technical quality, and produces ranked CSV output with explanations.

## Features

- **Multi-model composite scoring** - Uses Qwen, GPT-4o-mini, and Gemini for weighted consensus
- **Feature extraction** - Pixtral extracts scene type, lighting, composition details
- **Aesthetic scoring** - Composition, subject strength, visual appeal (0-100)
- **Technical scoring** - Sharpness, exposure, noise level (0-100)
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
# Basic usage
photo-score run --input /path/to/photos --output scores.csv

# With options
photo-score run \
  --input /path/to/photos \
  --output scores.csv \
  --config configs/default.yaml \
  --verbose
```

### Calibrate Scoring

Run composite scoring on a sample to verify model agreement:

```bash
photo-score calibrate \
  --input /path/to/photos \
  --output calibration_results.csv \
  --max-images 10
```

### Benchmark Models

Compare different vision models:

```bash
photo-score benchmark \
  --input /path/to/photos \
  --output benchmark_results.csv \
  --models qwen gpt-4o-mini gemini pixtral \
  --task aesthetic
```

### View Results

Launch the web viewer to review scored photos and submit corrections:

```bash
python serve_viewer.py --photos /path/to/photos --csv scores.csv
```

Open http://localhost:8080 to:
- View photos sorted by score
- See aesthetic/technical breakdowns
- Adjust scores with sliders
- Export corrections as JSON/CSV

## Scoring System

### Score Tiers

| Score | Tier | Description |
|-------|------|-------------|
| 85-100 | Excellent | Portfolio-worthy, exceptional |
| 70-84 | Strong | Intentional, well-executed |
| 50-69 | Competent | Solid, "camera did its job" |
| 30-49 | Tourist | Below average snapshot |
| 0-29 | Flawed | Technical issues, poor composition |

### Weights

**Aesthetic (60% of final score):**
- Composition: 40%
- Subject Strength: 35%
- Visual Appeal: 25%

**Technical (40% of final score):**
- Sharpness: 40%
- Exposure: 35%
- Noise Level: 25%

## Model Configuration

The composite scorer uses multiple models for robustness:

| Task | Model | Weight | Cost |
|------|-------|--------|------|
| Feature Extraction | Pixtral 12B | - | $0.10/M |
| Aesthetic Scoring | Qwen 2.5 VL 72B | 35% | $0.07/M |
| Aesthetic Scoring | GPT-4o-mini | 35% | $0.15/M |
| Aesthetic Scoring | Gemini 2.5 Flash | 30% | $0.30/M |
| Metadata | Pixtral 12B | - | $0.10/M |

**Cost per image:** ~$0.002 (8 API calls)

## Output Format

The CSV output includes:

```csv
image_path,final_score,aesthetic_score,technical_score,composition,subject_strength,visual_appeal,sharpness,exposure,noise_level,scene_type,lighting,description,location_name,location_country
```

## Project Structure

```
photo_score/
├── cli.py                 # Typer CLI commands
├── inference/
│   ├── client.py          # OpenRouter API client
│   ├── prompts.py         # Vision model prompts
│   └── schemas.py         # Pydantic response models
├── scoring/
│   ├── composite.py       # Multi-model scoring
│   ├── reducer.py         # Score computation
│   └── explanations.py    # Score explanations
├── storage/
│   ├── cache.py           # SQLite caching
│   └── models.py          # Data models
├── ingestion/
│   ├── discover.py        # Image discovery
│   └── metadata.py        # EXIF extraction
└── output/
    └── csv_writer.py      # CSV output
```

## Development

```bash
# Run tests
uv run pytest

# Run specific test
uv run pytest tests/test_reducer.py -v
```

## License

MIT
