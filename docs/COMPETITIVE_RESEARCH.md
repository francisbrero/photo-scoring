# Competitive Research: Photo Scoring & Quality Assessment

*Research conducted: December 2025*

## Executive Summary

Our photo-scoring project uses Vision Language Models (VLMs) via OpenRouter for nuanced photo quality assessment with detailed critiques. This research examines the competitive landscape to identify best practices, gaps, and opportunities.

**Key Finding:** Our VLM approach is cutting-edge (validated by CVPR 2025 papers) but we can learn from commercial tools' UX and consider hybrid approaches for cost/speed optimization.

---

## Open Source Libraries

### 1. IQA-PyTorch (pyiqa)
**Repository:** https://github.com/chaofengc/IQA-PyTorch
**Stars:** 2k+ | **License:** Apache 2.0

The most comprehensive open-source IQA toolbox with 30+ metrics.

**Key Features:**
- Simple API: `pip install pyiqa`
- GPU accelerated (much faster than MATLAB)
- Includes NIMA, MUSIQ, TOPIQ, BRISQUE, NIQE
- No-reference and full-reference metrics

**Usage Example:**
```python
import pyiqa
import torch

# Create metric
nima = pyiqa.create_metric('nima', device=torch.device('cuda'))

# Score image
score = nima('path/to/image.jpg')
```

**Relevance to Our Project:**
- Could be our local scoring backend (Issue #23)
- Enables hybrid mode: fast local filter + VLM critique (Issue #25)
- Zero API cost for basic scoring

---

### 2. idealo/image-quality-assessment (NIMA)
**Repository:** https://github.com/idealo/image-quality-assessment
**Stars:** 1k+ | **License:** Apache 2.0

NIMA implementation with separate aesthetic and technical models.

**Key Features:**
- Two models: aesthetic + technical (like our architecture!)
- MobileNet backbone for fast inference
- Pre-trained on AVA dataset
- Docker images for deployment

**Architecture Validation:**
Their two-model approach (aesthetic vs technical) validates our design decision to score these aspects separately.

---

### 3. DepictQA
**Repository:** https://github.com/XPixelGroup/DepictQA
**Status:** CVPR 2025 (cutting-edge)

Uses Vision Language Models for descriptive quality assessment.

**Key Features:**
- VLM-based (like us!)
- Provides natural language descriptions of quality
- Distribution-based scoring for uncertainty

**Validation:**
Our VLM approach is aligned with state-of-the-art research direction.

---

### 4. Q-Future / Q-Align
**Repository:** https://github.com/Q-Future
**Status:** ICML 2024

All-in-one foundation model for visual scoring (IQA, IAA, VQA).

**Key Features:**
- Single model for multiple quality tasks
- Fine-tunable to downstream datasets
- Q-Instruct: 200K dataset for training

---

## Commercial Photo Culling Software

### 1. Aftershoot
**Website:** https://aftershoot.com
**Pricing:** ~$120/year unlimited

**Standout Feature: Preference Learning**
> "The AI observes your culling, editing, and retouching choices, identifying patterns in your preferences. For instance, if you consistently favor photos with strong emotional impact over those with perfect sharpness, the AI will begin to prioritize emotion."

**Key Features:**
- AI learns from user behavior
- Prioritizes emotion over technical perfection
- Unlimited processing for flat rate

**Learning for Us:**
- User calibration (Issue #17) is a proven, valued feature
- Consider implicit learning from user corrections
- Emotional/storytelling aspects matter to photographers

---

### 2. Imagen Culling
**Website:** https://imagen-ai.com/culling

**Standout Feature: Lightroom Integration**
- Star ratings and color labels sync directly to Lightroom
- Groups similar images automatically
- Detects blinks, kisses, blur

**Rating System:**
- 4 stars = Unique Photos
- 5 stars = Keepers

**Learning for Us:**
- XMP sidecar export is essential (Issue #24)
- Grouping similar shots adds value
- Specific detection (blinks, etc.) could be features

---

### 3. Optyx
**Website:** https://www.optyx.app

**Standout Feature: Speed**
> "Cull 1000 photos in 60 seconds"

**Key Features:**
- Multiple AI models for different aspects
- Facial expression analysis
- Customizable rating output
- Analyzes: expression, sharpness, composition, exposure

**Learning for Us:**
- Local model speed is compelling
- Multi-model approach (like ours) is validated
- Customizable output format matters

---

### 4. FilterPixel
**Website:** https://filterpixel.com

**Standout Feature: Workflow Matching**
> "Tell FilterPixel how you use colors, stars, or tags, and the AI will mirror your system"

**Key Features:**
- Flags: blurred, closed eyes, underexposed
- Groups similar images
- Matches existing user workflow

**Learning for Us:**
- Adapting to user's existing system is important
- Don't force users to learn new workflow

---

### 5. Adobe Lightroom Classic (Assisted Culling)
**Feature:** Built-in assisted culling

**Key Features:**
- Subject Focus detection
- Eye Focus detection
- Eyes Open detection
- Batch flagging/rating

**Learning for Us:**
- Adobe sets baseline expectations
- Focus detection is table-stakes
- Batch operations are essential

---

## Competitive Positioning

### Our Advantages
| Aspect | Commercial Tools | Our Approach |
|--------|------------------|--------------|
| Feedback Quality | Stars/labels only | Detailed natural language critique |
| Educational Value | Minimal | Photography instructor feedback |
| Transparency | Black box | Multi-model with reasoning |
| Cost | $100-200/year | ~$5/1000 images |
| Flexibility | Fixed algorithms | Configurable weights |

### Our Gaps
| Gap | Commercial Standard | Our Status | Issue |
|-----|---------------------|------------|-------|
| Speed | 1000 photos/min | ~2 photos/min | #3, #23, #25 |
| Lightroom Integration | XMP export | CSV only | #24 |
| Preference Learning | Implicit + explicit | Planned | #17 |
| Similar Image Grouping | Automatic | Not implemented | Future |
| Blink/Expression Detection | Standard | Not implemented | Future |

---

## Research Papers & Models

### NIMA: Neural Image Assessment (Google, 2017)
**Paper:** https://arxiv.org/abs/1709.05424

**Key Innovation:** Predicts *distribution* of human opinion scores, not just mean.

**Architecture:**
- CNN backbone (Inception/MobileNet)
- Earth Mover's Distance loss
- Trained on AVA dataset (250K images)

**Relevance:**
- Could add confidence/distribution to our scores (Issue #26)
- Available in pyiqa for local scoring

---

### MUSIQ: Multi-scale Image Quality Transformer (Google, 2021)
**Paper:** https://arxiv.org/abs/2108.05997

**Key Innovation:** Handles any aspect ratio and resolution (no fixed input size).

**Relevance:**
- Our images come in various sizes/ratios
- Available in pyiqa
- Could be our primary local scorer

---

## Recommendations

### Immediate Priorities
1. **Add pyiqa integration** (Issue #23) - Enables free local scoring
2. **Add Lightroom XMP export** (Issue #24) - Industry standard
3. **Implement hybrid mode** (Issue #25) - 80% cost reduction

### Medium-term
4. **Add score confidence** (Issue #26) - Differentiated feature
5. **User preference learning** (Issue #17) - Proven market need
6. **Study Aftershoot UX** (Issue #27) - Best-in-class learning

### Long-term Considerations
- Similar image grouping (burst detection)
- Specific detections (blink, blur, exposure)
- Mobile app for on-device processing

---

## Cost Comparison

| Solution | Cost per 1000 images | Speed |
|----------|---------------------|-------|
| **Our VLM approach** | $5.00 | ~30 min |
| **Our hybrid (proposed)** | $1.00 | ~5 min |
| **Our local only** | $0.00 | ~1 min |
| Aftershoot | $10* | ~1 min |
| Optyx | $15* | ~1 min |

*Estimated based on yearly subscription / typical usage

---

## Related GitHub Issues

| Issue | Title | Priority |
|-------|-------|----------|
| #3 | Support local models for inference | High |
| #17 | Add user score calibration | High |
| #23 | Add pyiqa as local scoring backend | High |
| #24 | Add Lightroom XMP sidecar export | High |
| #25 | Add hybrid scoring mode | High |
| #26 | Add score confidence/distribution | Medium |
| #27 | Study Aftershoot UX for preference learning | Medium |

---

## References

### Open Source
- [IQA-PyTorch (pyiqa)](https://github.com/chaofengc/IQA-PyTorch)
- [idealo/image-quality-assessment](https://github.com/idealo/image-quality-assessment)
- [DepictQA](https://github.com/XPixelGroup/DepictQA)
- [Awesome-Image-Quality-Assessment](https://github.com/chaofengc/Awesome-Image-Quality-Assessment)
- [Q-Future](https://github.com/Q-Future)

### Commercial
- [Aftershoot](https://aftershoot.com/)
- [Imagen Culling](https://imagen-ai.com/culling/)
- [Optyx](https://www.optyx.app/)
- [FilterPixel](https://filterpixel.com/)
- [Adobe Lightroom Assisted Culling](https://helpx.adobe.com/lightroom-classic/help/assisted-culling.html)

### Papers
- [NIMA: Neural Image Assessment](https://arxiv.org/abs/1709.05424)
- [MUSIQ: Multi-scale Image Quality Transformer](https://arxiv.org/abs/2108.05997)
- [TOPIQ](https://github.com/chaofengc/IQA-PyTorch)
