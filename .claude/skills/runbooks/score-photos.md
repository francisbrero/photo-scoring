---
description: Step-by-step guide to score a batch of photos
globs: []
alwaysApply: false
---

# Runbook: Score Photos

## Prerequisites

- [ ] `OPENROUTER_API_KEY` environment variable set
- [ ] Photos directory exists with supported formats (.jpg, .jpeg, .png, .heic, .heif)

## Steps

### 1. Verify API Key
```bash
echo $OPENROUTER_API_KEY | head -c 10
```
Should show first 10 chars of your key.

### 2. Check Photo Count
```bash
find /path/to/photos -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.heic" -o -iname "*.heif" \) | wc -l
```

### 3. Estimate Cost
```
Cost = photo_count × $0.005
```
| Photos | Cost |
|--------|------|
| 10 | $0.05 |
| 100 | $0.50 |
| 1000 | $5.00 |

### 4. Run Scoring
```bash
cd /Users/francis/Documents/MadKudu/photo-scoring

# Score all photos
uv run python calibrate.py -i /path/to/photos -o results.csv

# Or limit to N photos (for testing)
uv run python calibrate.py -i /path/to/photos -o results.csv -n 10
```

### 5. Review Results
```bash
# Quick summary
head -20 results.csv

# Start web viewer
uv run python serve_viewer.py --photos /path/to/photos --csv results.csv
```
Open http://localhost:8080

## Troubleshooting

### "API key required" error
```bash
export OPENROUTER_API_KEY="your-key-here"
```

### Rate limiting (429 errors)
The client handles this automatically with exponential backoff. If persistent, wait a few minutes.

### HEIC files not working
```bash
uv add pillow-heif
```

## Output

CSV file with columns:
- `image_path`, `final_score` (0-100)
- `aesthetic_score`, `technical_score` (0-1)
- `composition`, `subject_strength`, `visual_appeal` (0-1)
- `sharpness`, `exposure`, `noise_level` (0-1)
- `scene_type`, `lighting`, `description`
- `explanation`, `improvements`
