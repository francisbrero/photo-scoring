# Score Photos

Score a batch of photos using the calibration script.

## Usage
```
/score-photos [directory] [options]
```

## Instructions

When the user invokes this skill:

1. **Check for API key**
   ```bash
   echo $OPENROUTER_API_KEY | head -c 10
   ```
   If not set, remind user to set `OPENROUTER_API_KEY` environment variable.

2. **Determine input directory**
   - If user provided a directory, use that
   - Otherwise, ask which directory to score

3. **Run calibration script**
   ```bash
   cd /Users/francis/Documents/MadKudu/photo-scoring
   uv run python calibrate.py -i [directory] -o results.csv -n [count]
   ```
   Default count is all photos. Use `-n 10` for quick test.

4. **Report results**
   - Show summary: total photos, average score, score distribution
   - Offer to start the web viewer

## Options
- `-n [count]` - Limit to N photos (for testing)
- `--no-viewer` - Skip starting web viewer after scoring

## Example
```
/score-photos ~/Photos/vacation -n 20
```
