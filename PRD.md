# Personal Photo Scoring CLI — Product Requirements Document (PRD)

## Project Name

Personal Photo Scoring CLI

## Goal

Provide a command-line tool that recursively analyzes large photo collections and produces a CSV ranking images by quality, with transparent, diagnostic explanations designed to help the user iteratively refine scoring weights.

The system optimizes for reproducibility, debuggability, and fast iteration on personal aesthetic preferences.

---

## Core Principles

1. Inference once, score many times
   Vision model inference is expensive. All scoring and explanation logic must be re-runnable instantly from cached attributes.

2. Explanations are diagnostic
   Explanations should help the user understand why an image scored as it did and what configuration changes would alter similar outcomes.

3. Determinism over cleverness (MVP)
   No learning or free-form LLM explanations. All outputs are derived deterministically from scores, weights, and thresholds.

---

## Core User Workflow

1. User runs the CLI against a root photo directory.
2. The tool recursively discovers all supported images in subdirectories.
3. Vision models extract attributes once per image.
4. Attributes are normalized and cached locally.
5. A configuration-driven reducer computes scores.
6. A CSV is generated containing scores, attribute breakdowns, and diagnostic explanations.

Files are never moved or modified in the MVP.

---

## CLI Interface

Example invocation:

```
photo-score run \
  --input ./photos/japan \
  --config ./configs/default.yaml \
  --output ./outputs/japan_scores.csv
```

Required arguments:

* `--input`: root directory to scan (recursive)
* `--config`: scoring configuration file
* `--output`: CSV output path

Optional flags (MVP):

* `--overwrite`
* `--verbose`
* `--extensions`

---

## Functional Requirements

### 1. Recursive Image Discovery

* Traverse all subdirectories under the input path
* Supported formats: JPEG, PNG, HEIC
* Ignore non-image files
* Stable, deterministic ordering

Each image record includes:

* `image_id` (hash-based)
* relative file path
* filename
* EXIF metadata (when available)

---

### 2. Vision Model Inference

* OpenRouter is used for model access in the MVP
* Models are defined in configuration
* Each image is processed once per model version
* Raw model outputs are cached locally

#### MVP Model Choice

* Claude 3.5 Sonnet Vision

#### Inference Passes

* Aesthetic vector extraction
* Technical signal extraction

---

### 3. Attribute Extraction and Normalization

All attributes are normalized to a [0, 1] range and stored independently.

#### Aesthetic Vector (Small, Explicit)

* `composition`
* `subject_strength`
* `visual_appeal`

#### Technical Attributes

* `sharpness`
* `exposure_balance`
* `noise_level`

Each attribute stores:

* value
* source model
* model version

---

### 4. Configurable Scoring Reducer

The reducer computes:

* Aggregate category scores (technical, aesthetic)
* Final score (normalized to 0–100)

Reducer characteristics:

* Weighted sum
* Optional hard thresholds (e.g. minimum sharpness)
* Deterministic and reproducible

The reducer must expose per-attribute contribution values for explanation generation.

---

### 5. Explanation Engine (Key MVP Feature)

Each image receives a 2–3 sentence explanation structured as:

1. Primary positive contributors
2. Primary penalties
3. Weight-tuning insight

Example:

> “This image scores highly due to strong composition and subject clarity, which dominate under the current aesthetic weighting. Visual appeal contributes moderately, while sharpness applies a small penalty. Increasing the sharpness weight would significantly lower the score of similar images.”

Explanation requirements:

* Template-driven
* Weight-aware and contribution-aware
* Deterministic
* Optimized for CSV readability

---

### 6. CSV Output

One row per image.

Required columns:

* `image_path`
* `final_score`
* `technical_score`
* `aesthetic_score`
* `attributes` (JSON-serialized)
* `explanation`

Optional columns:

* `config_version`
* `model_versions`

The CSV must be deterministic, sortable, and compatible with Excel and data tools.

---

## Configuration System

* Format: YAML (preferred) or JSON
* Versioned and stored alongside outputs

Configuration controls:

* Model selection
* Enabled attributes
* Attribute weights
* Category weights
* Thresholds

Changing the configuration must allow instant re-scoring without re-running inference.

---

## Non-Functional Requirements

Performance:

* ~1,000 images processed in ~10 minutes for initial inference
* Re-scoring completes in seconds

Reproducibility:

* Same input, same config, same model versions produce identical CSV output

Extensibility:

* Learning systems can later modify weights
* Technical models can be swapped for local inference

Privacy:

* Architecture must support full local execution in the future

---

## Explicit Non-Goals (MVP)

* GUI or web interface
* Automatic learning or feedback loops
* File movement or tagging
* Face recognition or people clustering
* Cloud persistence

---

## MVP Status

This PRD defines an implementation-ready MVP.

Next logical follow-ups:

* Lock exact prompt contracts and JSON schemas
* Define reducer math formally
* Define explanation templates
* Produce a step-by-step implementation plan
