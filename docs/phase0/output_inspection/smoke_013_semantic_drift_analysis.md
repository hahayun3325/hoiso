# Smoke 013 — Semantic Drift Analysis

## Input case

Dataset: HO3D v3
Split: train
Sequence: GPMF13
Frame: 0873

## Main observation

The successful low-memory smoke run produced clear hand/object pose and good hand-object alignment.

However, the reconstructed object appears more like a generic rounded can than the likely input object, a rectangular SPAM tin.

## Gemini response

The Gemini response used by the pipeline was:

A can of Spam.

This is semantically correct but geometrically underspecified. It does not describe the object as rectangular, boxy, flat-faced, or non-cylindrical.

## Likely failure chain

input image→ generic object description→ inpainting produces generic can-like completion→ 3D generation follows the wrong object prior→ low-memory extraction preserves a plausible but semantically drifted object

## Interpretation

This is not only a mesh-detail problem.

The mismatch likely begins around object understanding and inpainting, before final mesh extraction.

## Research motivation

This motivates:

- failure diagnosis
- structured object-description prompting
- confidence-guided coordination
- 2D-3D silhouette consistency checking
- contact-aware supervision
- physically aware refinement

## Key hypothesis

Contact-aware and confidence-aware coordination may recover interaction quality and reduce semantic drift when upstream geometry is imperfect.
