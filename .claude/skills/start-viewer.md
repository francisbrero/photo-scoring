# Start Viewer

Start the web viewer to review scored photos.

## Usage
```
/start-viewer [csv-file] [photos-directory]
```

## Instructions

When the user invokes this skill:

1. **Find the CSV file**
   - If user specified a CSV file, use that
   - Otherwise, look for recent CSV files:
     ```bash
     ls -lt *.csv 2>/dev/null | head -5
     ```
   - If no CSV found, suggest running `/score-photos` first

2. **Determine photos directory**
   - If user specified, use that
   - Otherwise, try to infer from CSV content or ask

3. **Start the server**
   ```bash
   cd /Users/francis/Documents/MadKudu/photo-scoring
   uv run python serve_viewer.py --photos [directory] --csv [csv-file] --port 8080
   ```
   Run in background so user can continue working.

4. **Report status**
   - Confirm server started
   - Provide URL: http://localhost:8080
   - Remind user how to stop: `kill %1` or Ctrl+C

## Example
```
/start-viewer results.csv ~/Photos/vacation
```
