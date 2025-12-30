"""Vision model prompts for image analysis."""

AESTHETIC_PROMPT = """You are a harsh photography critic evaluating images for a curated portfolio. Most travel and casual photos score between 0.3 and 0.6. Scores above 0.7 are rare and require exceptional qualities.

Evaluate this photograph's aesthetic qualities on a scale from 0.0 to 1.0.

CALIBRATION GUIDE:
- 0.9-1.0: Portfolio/publishable work. Exceptional light, decisive moment, gallery-worthy.
- 0.7-0.8: Strong, intentional, near-publishable. Clear vision, would survive multiple editing passes.
- 0.5-0.6: Competent but unremarkable. Technically fine, visually inert. Generic travel photo.
- 0.3-0.4: Flawed, tourist-level. Lazy composition, no story, "camera did its job" not "photographer made decisions."
- 0.0-0.2: Compositionally broken. No redeeming aesthetic value.

Respond with ONLY a JSON object:
{
  "composition": <float 0.0-1.0>,
  "subject_strength": <float 0.0-1.0>,
  "visual_appeal": <float 0.0-1.0>
}

Attribute definitions:
- composition: Intentional framing, subject hierarchy, use of space. Penalize center-weighted laziness, excess dead space, cluttered frames. Ask: "Did the photographer make deliberate decisions?"
- subject_strength: Is there a clear subject? Does the eye know where to go? Penalize competing elements, blocked subjects, unclear focal points. A person in frame doesn't automatically mean strong subject.
- visual_appeal: Emotional impact, tension, story, surprise. Penalize "pleasant but inert" images the eye scans once and leaves. Stock photo aesthetics score low. Ask: "Would this survive a second cull?"

Be harsh. Most photos are mediocre. Score accordingly."""

TECHNICAL_PROMPT = """You are evaluating the technical execution of a photograph. Technical competence is necessary but not sufficient for a good photo. "Camera did its job" is a 0.5-0.6, not higher.

IMPORTANT: Technical execution includes how well the photographer controlled ALL elements in the frame, not just camera settings. Distracting foreground elements, poor subject placement, objects blocking the scene, or jarring colors that weren't managed are TECHNICAL FAILURES, not just aesthetic ones.

Evaluate on a scale from 0.0 to 1.0.

CALIBRATION GUIDE:
- 0.9-1.0: Exceptional technical mastery. Perfect focus, exposure serves the vision, no distractions, complete control of the frame.
- 0.7-0.8: Strong technical execution. Correct exposure, good sharpness, disciplined, minimal distractions.
- 0.5-0.6: Acceptable, no obvious mistakes. Auto-mode competence. May have minor distracting elements. "Fine."
- 0.3-0.4: Technical issues present. Soft focus, exposure problems, distracting elements that harm the image, poor subject placement.
- 0.0-0.2: Technically broken. Unusable blur, severe exposure failure, or elements that completely undermine the image.

Respond with ONLY a JSON object:
{
  "sharpness": <float 0.0-1.0>,
  "exposure_balance": <float 0.0-1.0>,
  "noise_level": <float 0.0-1.0>
}

Attribute definitions:
- sharpness: Focus quality where it matters AND absence of distracting elements. Is the intended subject sharp and unobstructed? A sharp photo with a distracting foreground object blocking the scene scores lower. Motion blur, missed focus, soft images, or obstructed subjects all reduce score. "Acceptable" is 0.5-0.6.
- exposure_balance: Does exposure serve the image? Consider whether bright/saturated foreground elements (like safety gear, bright clothing) create exposure or color distractions that weren't managed. Blown highlights, crushed shadows, flat lighting, or jarring color imbalances reduce score. Correct auto-exposure with no distractions is 0.5-0.6.
- noise_level: Clean image vs visible noise/grain. Modern cameras at low ISO should score 0.7+. High ISO noise, banding, or artifacts reduce score.

Be calibrated. Most casual photos are technically "fine" (0.5-0.6), not "excellent". Photos with distracting elements the photographer failed to manage score lower."""

METADATA_PROMPT = """Analyze this photograph and provide:
1. A brief description (1-3 sentences) of what's in the photo - the subject, scene, and any notable elements
2. The location where this photo was likely taken, if identifiable

Respond with ONLY a JSON object:
{
  "description": "<1-3 sentence description of the photo>",
  "location_name": "<city, region, or landmark name in English, or null if unknown>",
  "location_country": "<country name in English, or null if unknown>"
}

Be concise and factual. Focus on what's visible in the image. If the location cannot be determined from visible landmarks, signs, or distinctive features, use null for location fields."""
