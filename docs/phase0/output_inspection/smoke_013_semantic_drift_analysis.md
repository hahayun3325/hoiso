# Smoke 013 — Semantic Drift Analysis

## Main observation

The successful low-memory smoke run produced clear hand/object pose and good alignment.
However, the reconstructed object appears more like a generic rounded can than the likely input object, a SPAM can.

## Likely failure chain

input image
→ object understanding / Gemini description may be too generic
→ inpainting produces a generic can-like completion
→ 3D generation follows the wrong object prior
→ low-memory extraction preserves a plausible but semantically drifted object shape

## Interpretation

This is not only a mesh-detail problem.
The mismatch seems to begin from the inpainting / object-understanding stage.

## Why this matters

This failure motivates:
- failure diagnosis,
- confidence-guided coordination,
- contact-aware supervision,
- physically aware refinement.

## Hypothesis

Better contact-aware and confidence-aware coordination may recover interaction quality and reduce semantic drift, even when upstream geometry is imperfect.
