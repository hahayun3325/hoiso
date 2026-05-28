# Phase 0.15c — Confidence-Guided Object Fallback Result

## Goal

Recover object completeness after final guidance fragments the object mesh.

## Problem

The final guided object from smoke022 remains fragmented even when object pose and object-noise learning rates are frozen.

## Candidate objects

### Hunyuan initial object

- complete object shape
- 1 connected component
- fragmentation score = 0.0

### smoke022 final guided object

- fragmented object shape
- 4 connected components
- fragmentation score = 3.4585

## Selection result

The confidence-guided selector chooses the Hunyuan initial object as the trusted object source.

## Alignment result

Two diagnostic scenes were generated:

- `fallback_selected_object_plus_final_hand.png`
- `bbox_aligned_selected_object_plus_final_hand.png`

The bbox-aligned selected object gives a visually reasonable hand-object alignment while preserving the complete object shape.

## Interpretation

The fallback module successfully fixes the object completeness problem at the source-selection level.

However, this is still a diagnostic fallback. The next step is to replace bbox alignment with contact-aware SE(3) alignment and local contact refinement.

## Research implication

This supports the HOLDSE-Flow idea:

- use foundation models to propose candidates,
- score each candidate by confidence,
- reject broken final-stage outputs,
- preserve object geometry,
- optimize hand-object alignment locally.
