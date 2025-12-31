---
description: Flask web viewer for reviewing scored photos, UI components
globs:
  - "serve_viewer.py"
  - "templates/**/*.html"
alwaysApply: false
---

# Web Viewer

## Overview

Use this skill when working with the Flask-based web viewer for reviewing scored photos.

## Running the Viewer

```bash
uv run python serve_viewer.py --photos /path/to/photos --csv results.csv --port 8080
```

## Architecture

```
serve_viewer.py
├── Flask app with routes:
│   ├── GET /           - Main viewer page (HTML)
│   ├── GET /api/photos - Photo data (JSON)
│   └── GET /image/<path> - Serve image (JPEG)
└── On-the-fly HEIC→JPEG conversion
```

## Key Features

### HEIC Support
```python
from PIL import Image, ImageOps

def convert_image_to_jpeg(filepath: Path) -> bytes:
    with Image.open(filepath) as img:
        img = ImageOps.exif_transpose(img)  # Fix rotation
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return buffer.getvalue()
```

### UI Components
- Photo grid with scores
- Expandable critique sections (collapsed by default)
- Score breakdown bars
- Cost badge (~$0.005/image)

### CSS Classes
```css
.photo-card        /* Individual photo container */
.score-badge       /* Score display (color-coded) */
.expandable        /* Collapsible sections */
.expandable.open   /* Expanded state */
.score-bar         /* Visual score bars */
```

## Customization

### Score Colors
```javascript
function getScoreColor(score) {
    if (score >= 85) return '#22c55e';  // green
    if (score >= 70) return '#84cc16';  // lime
    if (score >= 50) return '#eab308';  // yellow
    if (score >= 30) return '#f97316';  // orange
    return '#ef4444';                    // red
}
```

## Resources

- [serve_viewer.py](serve_viewer.py) - Main server file
