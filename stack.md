Given our constraints (Mac, Claude Code, Python, common libraries, CLI-first), the stack below is pragmatic, boring in the right ways, and maps cleanly to the PRD.


### Language and runtime

**Python 3.11**

Reasons:

* Best ecosystem for image handling and data workflows
* Excellent CLI tooling
* Strong support in Claude Code
* Easy path to local ML later

Avoid 3.12 for now due to uneven support in some ML/image libraries.

---

### CLI framework

**Typer**

Why:

* Clean, modern CLI UX
* Type hints become CLI args
* Excellent help output
* Minimal boilerplate

This will give you a CLI that feels intentional rather than hacked together.

---

### Image handling

**Pillow (PIL fork)**
Primary image loading and format support.

**pillow-heif**
Required for HEIC support on macOS.

These are stable, ubiquitous, and good enough. Do not overcomplicate with OpenCV unless you truly need it.

---

### Metadata extraction

**piexif** or **exifread**

Use only for lightweight EXIF parsing:

* Timestamp
* Camera
* Lens
* GPS (optional)

Do not over-index on metadata in MVP.

---

### Model access (OpenRouter)

**requests** or **httpx**

Keep this explicit and thin:

* One module that wraps OpenRouter calls
* Strict request and response schemas
* Easy to stub or replace later

Avoid OpenRouter SDK abstractions if they hide too much. You want full control over prompts and outputs.

---

### Data modeling and validation

**pydantic v2**

Critical for this project.

Use it to:

* Define attribute schemas
* Validate model outputs
* Version model responses
* Enforce numeric bounds [0, 1]

This is your first line of defense against model drift.

---

### Caching and persistence

**SQLite** (via stdlib `sqlite3` or `sqlmodel`)

Why:

* Zero infrastructure
* Fast enough
* Deterministic
* Easy to inspect

Use it to store:

* image_id
* file path
* raw model outputs
* normalized attributes
* model versions

Avoid JSON files for caching once you pass a few hundred images.

---

### Scoring and explanation logic

**Pure Python + dataclasses**

Keep this logic:

* Fully deterministic
* Side-effect free
* Easy to unit test

Do not use pandas here. This is business logic, not data analysis.

---

### CSV output

**Python stdlib `csv`**

Reasons:

* Deterministic output
* No hidden type coercion
* Complete control over column order

Pandas is unnecessary and can introduce subtle formatting issues.

---

### Logging

**stdlib `logging`**

Simple, predictable, no magic.

Add:

* INFO for progress
* DEBUG for model responses
* WARNING for skipped files or invalid outputs

Avoid structured logging in MVP.

---

### Testing

**pytest**

Focus tests on:

* Reducer math
* Explanation generation
* Config parsing
* Attribute normalization

Do not test model quality. Test contracts and determinism.

---

### Project layout (recommended)

```
photo_score/
  cli/
    main.py
  ingestion/
    discover.py
    metadata.py
  inference/
    openrouter.py
    prompts.py
    schemas.py
  scoring/
    reducer.py
    explanations.py
  storage/
    cache.py
    models.py
  config/
    loader.py
    schema.py
  output/
    csv_writer.py
  utils/
    hashing.py
    logging.py
tests/
configs/
```

This mirrors your PRD layers almost one-to-one.

---

### Explicitly avoid (for now)

* Pandas
* OpenCV
* Async frameworks
* ORMs heavier than SQLite helpers
* Agent frameworks
* Any ML training libraries

You want this to feel like a **deterministic data pipeline**, not an ML research project.

---