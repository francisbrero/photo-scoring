# Implementation Plan: Issue #72 - Grid-Based Visual Triage

## Overview

Add a `photo-score triage` command that uses composite grid images to quickly identify the top X% of photos from large collections (2000+ photos).

## Architecture

```
photo_score/triage/
├── __init__.py           # Module exports
├── grid.py               # Grid image generation with coordinate labels
├── prompts.py            # Triage-specific prompts (coarse & fine)
├── selector.py           # Multi-model selection with union consensus
└── output.py             # Symlink folder creation
```

## Implementation Phases

### Phase 1: ADR Documentation
- [x] Create `docs/adr/009-grid-triage.md`
- Document two-pass approach, cost analysis, trade-offs

### Phase 2: Grid Generation (`grid.py`)
- [ ] `GridGenerator` class
- [ ] `generate_grid(images: list[Path], grid_size: int) -> tuple[Image, dict[str, Path]]`
  - Resize photos to thumbnails (~100px for 20x20, ~512px for 4x4)
  - Create composite image with coordinate labels (A-T rows, 1-20 cols)
  - Return mapping of coordinates to original file paths
- [ ] Handle uneven grids (last grid may be smaller)
- [ ] Support HEIC via pillow_heif

### Phase 3: Prompts (`prompts.py`)
- [ ] `COARSE_TRIAGE_PROMPT`: For 20x20 grids, asks for stand-out photos
- [ ] `FINE_TRIAGE_PROMPT`: For 4x4 grids, more detailed evaluation
- [ ] `get_triage_prompt(criteria, target_percentage, grid_coords)` function
- [ ] Criteria variants: `standout`, `quality`, custom text

### Phase 4: Selector (`selector.py`)
- [ ] `TriageSelector` class using existing `OpenRouterClient`
- [ ] Models: Qwen 2.5 VL 72B + Gemini 2.5 Flash (union consensus)
- [ ] `select_from_grid(grid_image, prompt, models) -> set[str]` (coordinates)
- [ ] Parse grid coordinates from responses (regex: `[A-T]\d{1,2}`)
- [ ] `run_triage(images, target, criteria, passes) -> list[Path]`
  - Pass 1: 20x20 coarse selection
  - Pass 2: 4x4 fine refinement on survivors

### Phase 5: Output (`output.py`)
- [ ] `create_selection_folder(selected: list[Path], output_dir: Path)`
- [ ] Create symlinks preserving original filenames
- [ ] Handle name collisions with numbered suffixes
- [ ] Return count of created symlinks

### Phase 6: CLI Command (`cli.py`)
- [ ] Add `triage` command:
```python
@app.command()
def triage(
    input_dir: Annotated[Path, typer.Option("--input", "-i", help="Input directory")],
    output_dir: Annotated[Path, typer.Option("--output", "-o", help="Output directory for symlinks")],
    top: Annotated[str, typer.Option("--top", "-t", help="Target: '10%' or '50'")],
    criteria: Annotated[str, typer.Option("--criteria", "-c")] = "standout",
    passes: Annotated[int, typer.Option("--passes", "-p")] = 2,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
)
```

### Phase 7: Tests (`tests/test_triage.py`)
- [ ] Test grid generation with various image counts
- [ ] Test coordinate label generation (A1-T20)
- [ ] Test coordinate parsing from model responses
- [ ] Test union consensus logic
- [ ] Test symlink creation and collision handling

### Phase 8: Final Verification
- [ ] Run full test suite
- [ ] Run linting
- [ ] Manual test with sample photos

## Cost Analysis (2000 photos)

| Pass | Grids | Models | Calls | Est. Cost |
|------|-------|--------|-------|-----------|
| 1 (20x20) | 5 | 2 | 10 | ~$0.15 |
| 2 (4x4, 20% survive) | 25 | 2 | 50 | ~$0.25 |
| **Total** | | | **60** | **~$0.40** |

Target: Under $0.50 ✓

## Key Design Decisions

1. **Grid coordinates**: A-T rows (20), 1-20 columns = A1 to T20
2. **Union consensus**: Keep photo if EITHER model selects it (fewer false negatives)
3. **Two-pass refinement**: 20x20 coarse → 4x4 fine for accuracy
4. **Symlink output**: Preserve originals, create symlinks in output folder
5. **Criteria options**: standout (default), quality, or custom text
6. **Cache**: Grid images cached in existing SQLite DB (new table)

## Models Used

- **Coarse pass**: `qwen/qwen-2.5-vl-72b-instruct` + `google/gemini-2.5-flash-preview`
- **Fine pass**: Same models for consistency

## Files to Create/Modify

| File | Action |
|------|--------|
| `docs/adr/009-grid-triage.md` | Create |
| `photo_score/triage/__init__.py` | Create |
| `photo_score/triage/grid.py` | Create |
| `photo_score/triage/prompts.py` | Create |
| `photo_score/triage/selector.py` | Create |
| `photo_score/triage/output.py` | Create |
| `photo_score/cli.py` | Modify (add triage command) |
| `tests/test_triage.py` | Create |

## Success Criteria

- [ ] Process 2000 photos in under 5 minutes
- [ ] Cost under $0.50 for 2000 photos
- [ ] All tests pass
- [ ] Linting passes
