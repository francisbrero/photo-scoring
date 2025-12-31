# AI Photo Culling UX Research: Aftershoot, Imagen, and FilterPixel

*Research conducted for Issue #27 - Study Aftershoot UX for preference learning*

## Executive Summary

This document analyzes how leading AI photo culling tools (Aftershoot, Imagen AI, FilterPixel) implement preference learning to inform our implementation of score calibration (Issue #17).

**Key Findings:**
1. All three platforms use **implicit learning** from user corrections, not explicit thumbs up/down
2. Training requires **2,500-5,000 edited photos** for personalized profiles
3. **Sliders** for adjusting strictness are the primary explicit preference mechanism
4. **Side-by-side comparison** is a core UX pattern for similar/duplicate photos
5. **Transparency** about AI decisions is limited across all platforms

---

## 1. Aftershoot

### How Preference Learning Works

Aftershoot's AI learns through observation of user behavior:

> "The AI observes your culling, editing, and retouching choices, identifying patterns in your preferences. For instance, if you consistently favor photos with strong emotional impact over those with perfect sharpness, the AI will begin to prioritize emotion."

**Learning triggers:**
- User overrides AI selections (marking rejected as selected, or vice versa)
- Star rating changes
- Color label assignments
- Consistent patterns across multiple culling sessions

**Training requirements:**
- Culling: No minimum - learns incrementally from corrections
- Editing profiles: 2,500 minimum, 5,000 recommended

### Explicit Preference Controls

| Control | Description |
|---------|-------------|
| Genre selector | Portrait, event, wedding, etc. - changes AI behavior |
| Selection quantity slider | "Cull 800 down to 40 best shots" |
| Filter toggles | Enable/disable: Duplicates, Blurry, Closed Eyes |
| Sensitivity sliders | More right = fewer images, more left = more images |
| Duplicate grouping | Small groups vs large groups |

### Feedback Collection UX

**Rating system:**
- 5-star rating (like Lightroom)
- Color labels (green = keep, yellow = maybe, red = reject)
- Keyboard shortcuts: `X` = reject, `S` = select

**Image Scores feature:**
- Shows AI confidence score per image
- Can be toggled on/off (keyboard: `Q`)
- Helps users understand why AI made decisions

**Review modes:**
1. **Survey Mode** - Side-by-side comparison of similar images
2. **Loupe Mode** - Full-size preview with detailed flags
3. **Grid Mode** - Overview with keyboard overrides

### Transparency

- Shows why images were flagged (blur, closed eyes, duplicate)
- Image Scores provide quality ratings
- Limited transparency on *how* preferences affect future culls

### Key UX Patterns to Adopt

1. **Genre/style presets** - Pre-configured for different photography types
2. **Target quantity slider** - "Give me the best 40 out of 800"
3. **Survey mode** - Side-by-side comparison for similar shots
4. **Keyboard-first workflow** - Fast culling with shortcuts
5. **Incremental learning** - No upfront training required for culling

---

## 2. Imagen AI

### How Preference Learning Works

Imagen uses a **profile-based approach** with explicit training:

> "A Personal AI Profile learns how to edit photos from your own edited photos. It analyzes your editing decisions across different lighting, subjects, and conditions."

**Training requirements:**
- **3,000 photos minimum** for Personal AI Profile
- 24 hours to train initial profile
- Fine-tuning: Upload 50% of original training set (min 3,000)

**Continuous learning:**
- "Upload Final Edits" after each batch sends corrections back
- System builds updated profile when enough new data accumulated

### Explicit Preference Controls

| Control | Description |
|---------|-------------|
| Personal AI Profile | Trained on your 3,000+ edited images |
| Talent AI Profiles | Pre-made profiles from pro photographers |
| Preset-based profiles | Build profile from Lightroom preset + questionnaire |
| Culling strictness | Adjustable sensitivity for selections |
| Grouping criteria | Customize how similar images are grouped |

### Feedback Collection UX

**Editing workflow:**
1. Imagen applies AI edits
2. User reviews and tweaks in Lightroom
3. User clicks "Upload Final Edits"
4. System learns from differences

**Culling workflow:**
- Star ratings and flags
- Manual override of AI selections
- Learns from final gallery selections

### Unique Features

- **Edited preview culling** - See AI-edited version while culling
- **Profile duplication** - Clone profile to experiment with variations
- **Integrated editing + culling** - Same app, one workflow

### Transparency

- Shows edit adjustments applied
- Profile can be fine-tuned and tracked
- Limited visibility into *why* specific selections made

### Key UX Patterns to Adopt

1. **Profile system** - Save/load preference configurations
2. **Pre-made profiles** - "Talent profiles" from pros as starting points
3. **Fine-tuning workflow** - Structured way to improve AI over time
4. **Preset import** - Create profile from existing Lightroom preset

---

## 3. FilterPixel

### How Preference Learning Works

FilterPixel emphasizes **adaptive learning** from usage:

> "Through layers of machine learning, the algorithm not only distinguishes between sharp and blurry photos but also learns from your preferences over time. If you consistently select images with certain lighting or composition elements, the AI will learn to prioritize similar images."

**Training requirements:**
- Culling: No minimum - learns from corrections
- Editing profiles: 3,000 Lightroom images

**Learning triggers:**
- Manual changes to AI selections
- Consistent selection patterns across sessions

### Explicit Preference Controls

| Control | Description |
|---------|-------------|
| AI Sliders | Adjust strictness thresholds |
| Magic Number | Target gallery size for delivery |
| Rating system customization | Tell AI how you use stars/colors/tags |
| Genre selection | Wedding, portrait, family, newborn |
| Sharpness/exposure thresholds | Per-project customization |

### Feedback Collection UX

**Review Mode:**
- Side-by-side comparison with face tracking
- Accept, swap, or refine selections
- Groups similar photos for deliberate choices

**Key principles:**
- No auto-deletes - AI flags, user decides
- No forced styles - adapts to your workflow
- Manual approval for all destructive actions

### Upcoming Features

- **Deep Culling** (announced) - "Context-aware AI that learns how you decide, not just which photos you keep"

### Transparency

- Flags technical issues (blur, closed eyes, exposure)
- Groups similar shots visually
- Explains why images were flagged

### Key UX Patterns to Adopt

1. **Magic Number** - Target delivery quantity
2. **Workflow mirroring** - AI uses same rating system as user
3. **No auto-delete** - AI suggests, user confirms
4. **Review mode** - Structured comparison workflow

---

## Comparative Analysis

### Feature Comparison Matrix

| Feature | Aftershoot | Imagen | FilterPixel | Our Implementation |
|---------|------------|--------|-------------|-------------------|
| **Implicit learning** | Yes (from corrections) | Yes (upload final edits) | Yes (from corrections) | TBD |
| **Explicit preferences** | Genre, sliders, toggles | Profile system | Sliders, magic number | TBD |
| **Training required** | None (culling) | 3,000 photos | None (culling) | TBD |
| **Preset styles** | Genre presets | Talent profiles | Expert profiles | Planned |
| **Side-by-side compare** | Survey mode | Limited | Review mode | Planned (#15) |
| **Target quantity** | Yes (slider) | Yes | Yes (magic number) | TBD |
| **Transparency** | Image scores | Edit preview | Flag reasons | TBD |
| **Feedback mechanism** | Star/color override | Upload final edits | Selection override | TBD |

### Personalization Approaches

| Approach | Description | Time to Value | Accuracy |
|----------|-------------|---------------|----------|
| **No training** | Learns from corrections | Immediate | Low initially, improves |
| **Preset/genre** | Pre-configured defaults | Immediate | Medium |
| **Profile training** | 3,000+ edited photos | 24 hours | High |
| **Continuous fine-tuning** | Ongoing corrections | Ongoing | Highest |

---

## Recommendations for Photo Score

Based on this research, here are recommendations for implementing Issue #17 (User Score Calibration):

### 1. Feedback Collection (Priority: High)

**Recommended approach: Implicit learning from corrections**

Instead of explicit thumbs up/down:
- Track when users mark an AI score as "too high" or "too low"
- Record the expected score via slider
- Learn weight adjustments from correction patterns

**UI pattern:**
```
Score: 72
[Too Low] [About Right] [Too High]

If "Too Low" or "Too High" clicked:
"What score would you give this? [____]"
```

### 2. Style Presets (Priority: High)

Create pre-configured weight profiles:
- **Portrait** - Emphasize subject, face detection
- **Landscape** - Emphasize composition, visual appeal
- **Street** - Emphasize moment, emotion
- **Technical** - Emphasize sharpness, exposure

Users select preset, then customize.

### 3. Explicit Weight Adjustment (Priority: Medium)

Provide sliders for power users:
```
Attribute Weights:
Composition    [======|====] 0.6
Sharpness      [====|======] 0.4
Subject        [========|==] 0.8
Visual Appeal  [=====|=====] 0.5
```

### 4. Target-Based Culling (Priority: Medium)

"Show me the best N photos" feature:
- User sets target: "Top 20 from this batch"
- AI adjusts threshold to meet target
- Similar to Aftershoot's quantity slider

### 5. Transparency (Priority: High)

Show why a photo scored what it did:
```
Score: 72

Why this score?
- Composition: 0.8 (contributed +24)
- Sharpness: 0.6 (contributed +12)
- Subject: 0.9 (contributed +27)
- Exposure: 0.3 (contributed +9, below threshold)
```

This already exists in our `explanations.py` - surface it in UI.

### 6. Comparison Mode (Priority: Medium)

Implement Survey/Review mode for Issue #15:
- Group similar photos (by timestamp, subject)
- Show side-by-side with scores
- "Pick winner" button
- Track picks to learn preferences

---

## Questions Answered

From the original issue:

| Question | Answer |
|----------|--------|
| How many photos needed before personalization kicks in? | **None for culling** - learns incrementally. **3,000-5,000** for editing profiles. |
| How is feedback collected? | **Implicit** - corrections to AI selections, star ratings, override patterns. Not thumbs up/down. |
| Can users explicitly set preferences vs implicit learning? | **Both** - Sliders/toggles for explicit, corrections for implicit. |
| How transparent is the system about what it learned? | **Limited** - Shows flags and scores, but not "I learned you prefer X". |
| Can preferences be reset or exported? | **Yes** for profiles (Imagen), **unclear** for implicit learning. |

---

## Implementation Priority

For Issue #17 implementation, recommended order:

1. **Style presets** - Immediate value, low effort
2. **Score correction UI** - "Too high/too low" buttons
3. **Weight sliders** - For power users
4. **Implicit learning backend** - Track corrections, suggest adjustments
5. **Target quantity** - "Best N photos" feature

---

## Sources

- [Aftershoot - Setting AI-Automated Culling Preferences](https://support.aftershoot.com/en/articles/6508163-setting-your-ai-automated-culling-preferences-in-aftershoot)
- [Aftershoot - AI Culling vs LR Culling](https://aftershoot.com/blog/ai-culling-vs-lr-culling/)
- [Aftershoot - Photo Culling Workflow Guide](https://aftershoot.com/blog/photo-culling-workflow/)
- [Aftershoot - Keyboard Shortcuts](https://support.aftershoot.com/en/articles/5227867-aftershoot-keyboard-shortcuts)
- [Imagen - What is a Personal AI Profile](https://support.imagen-ai.com/hc/en-us/articles/6069711141009-What-is-a-Personal-AI-Profile)
- [Imagen - Fine-tune your Personal AI Profile](https://support.imagen-ai.com/hc/en-us/articles/6069799037457-Fine-tune-your-Personal-AI-Profile)
- [Imagen - Culling Studio](https://imagen-ai.com/culling/)
- [FilterPixel - AI Photo Culling](https://filterpixel.com/culling)
- [FilterPixel - How AI Culling Algorithms Work](https://filterpixel.com/blog/how-ai-powered-photo-culling-algorithms-are-revolutionizing-image-selection-and-organization)
- [Shotkit - Aftershoot Review 2025](https://shotkit.com/aftershoot-review/)
- [SLR Lounge - Imagen Review](https://www.slrlounge.com/imagen-review/)
- [Breath Your Passion - AI Software Comparison](https://www.breatheyourpassion.com/blog/AISoftwareComparison)
