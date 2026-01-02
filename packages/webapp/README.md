# Photo Score Viewer - Web Frontend

React + TypeScript + Tailwind CSS v4 frontend for the Photo Score Viewer.

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

# Lint code
npm run lint
```

**Note:** During development, you need to run the Python backend separately:

```bash
# From repo root
uv run python serve_viewer.py --photos ./test_photos --csv test_photos_results.csv
```

The Vite dev server proxies `/api/*` and `/photos/*` to `localhost:8080`.

## Architecture

```
src/
├── components/
│   ├── Layout.tsx           # Page layout with header and theme toggle
│   ├── FilterBar.tsx        # Sort/filter controls
│   ├── PhotoGrid.tsx        # Responsive photo card grid
│   ├── PhotoCard.tsx        # Individual photo with scores and metadata
│   ├── ScoreBreakdown.tsx   # Aesthetic/technical metrics display
│   ├── CorrectionForm.tsx   # User score adjustment sliders
│   ├── Expandable.tsx       # Collapsible sections for critique/improvements
│   ├── Lightbox.tsx         # Full-screen image view with navigation
│   ├── ExportPanel.tsx      # Export corrections buttons
│   └── ThemeToggle.tsx      # Dark/light theme switcher
├── hooks/
│   ├── usePhotos.ts         # Fetch photo data from API
│   ├── useFilters.ts        # Sort/filter state and computed stats
│   ├── useCorrections.ts    # User corrections with localStorage persistence
│   └── useTheme.ts          # Theme preference management
├── types/
│   └── photo.ts             # TypeScript interfaces and utilities
├── App.tsx                  # Main application component
├── main.tsx                 # Entry point
└── index.css                # Tailwind CSS with theme variables
```

## Theming

Uses CSS variables for dark/light theme support:

```css
:root {
  --bg-primary: #1a1a2e;     /* Main background */
  --bg-secondary: #16213e;   /* Card background */
  --bg-tertiary: #0f3460;    /* Accent background */
  --text-primary: #f3f4f6;   /* Primary text */
  --text-secondary: #9ca3af; /* Secondary text */
  --text-muted: #6b7280;     /* Muted text */
  --border-color: #0f3460;   /* Borders */
}

.light-theme {
  --bg-primary: #f8fafc;
  --bg-secondary: #ffffff;
  /* ... */
}
```

Theme preference is persisted to localStorage.

## Features

- **Photo Grid** - Responsive 1-4 column grid with score overlays
- **Lightbox** - Full-screen view with prev/next navigation (← → arrow keys, ESC to close)
- **Score Display** - Color-coded scores with aesthetic/technical breakdown
- **Sorting** - By score (high/low), filename, aesthetic, or technical
- **Corrections** - Adjust scores with sliders, add notes, persist to localStorage
- **Export** - Download corrections as JSON or updated CSV
- **Theme Toggle** - Dark/light theme with persistence
- **Lazy Loading** - Images load on scroll for performance

## API Endpoints

Expected from backend:

- `GET /api/photos` - Array of photo objects with scores and metadata
- `GET /photos/:path` - Serve photo images (with automatic HEIC→JPEG conversion)

## Deployment

### Local (with Python backend)

```bash
# Build React app
npm run build

# Start Python server (automatically serves React from dist/)
cd ../..
uv run python serve_viewer.py --photos ./test_photos --csv ./test_photos_results.csv
# Open http://localhost:8080
```

### Vercel (Cloud)

The `vercel.json` configures:
- Build command and output directory
- Rewrites for API calls to backend (Railway/etc.)
- Cache headers for static assets
- Security headers

**Required Environment Variables:**

Set these in Vercel project settings:

| Variable | Description | Example |
|----------|-------------|---------|
| `BACKEND_URL` | URL of the Python backend API | `https://photo-scoring.up.railway.app` |

```bash
# Deploy to Vercel
vercel

# Or link to existing project
vercel link
vercel env add BACKEND_URL
vercel deploy --prod
```

## Tech Stack

- **React 19** - UI components
- **TypeScript** - Type safety
- **Vite 7** - Build tool with HMR
- **Tailwind CSS v4** - Utility-first styling with CSS variables
