# Photo Score Viewer - Web Frontend

React + TypeScript + Tailwind CSS frontend for the Photo Score Viewer.

## Development

```bash
# Install dependencies
npm install

# Start dev server (connects to Python backend on port 8080)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Architecture

```
src/
├── components/
│   ├── Layout.tsx           # Page layout with header
│   ├── FilterBar.tsx        # Sort/filter controls
│   ├── PhotoGrid.tsx        # Photo card grid
│   ├── PhotoCard.tsx        # Individual photo with scores
│   ├── ScoreBreakdown.tsx   # Aesthetic/technical metrics
│   ├── CorrectionForm.tsx   # User score adjustments
│   ├── Expandable.tsx       # Collapsible sections
│   ├── Lightbox.tsx         # Full-screen image view
│   └── ExportPanel.tsx      # Export buttons
├── hooks/
│   ├── usePhotos.ts         # Fetch photo data
│   ├── useFilters.ts        # Sort/filter state
│   └── useCorrections.ts    # User corrections state
├── types/
│   └── photo.ts             # TypeScript interfaces
├── App.tsx                  # Main application
└── main.tsx                 # Entry point
```

## Integration with Python Backend

During development, Vite proxies `/api/*` and `/photos/*` to `localhost:8080`.

For production, the Python server (`serve_viewer.py`) serves the built React app from `dist/`.

## Deployment

### Vercel (Cloud)

The `vercel.json` configures:
- Build command and output directory
- Rewrites for API calls to Railway backend
- Cache headers for static assets

```bash
# Deploy to Vercel
vercel
```

### Local (with Python backend)

```bash
# Build React app
npm run build

# Start Python server (serves React from dist/)
cd ../..
uv run python serve_viewer.py --photos ./test_photos --csv ./test_photos_results.csv
```

## Features

- **Photo Grid** - Responsive grid with score overlays
- **Lightbox** - Full-screen image viewing with keyboard navigation
- **Score Display** - Color-coded scores with aesthetic/technical breakdown
- **Sorting** - By score, filename, aesthetic, or technical
- **Corrections** - Adjust scores with sliders, persist to localStorage
- **Export** - Download corrections as JSON or updated CSV
- **Dark Theme** - Matches existing viewer design
