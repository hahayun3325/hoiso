# Phase 0.17 — Selector Between Phase 4.2 and Phase 4.3 Implementation Plan

## Goal

Move the selector from post-hoc replacement to an internal pipeline stage.

The selector should run after object-focused refinement and before final hand-object alignment.

## Current problem

The current post-hoc selector can choose `initial_obj`, but `initial_obj` may be a full Hunyuan HOI mesh rather than an object-only mesh.

This can cause:

- extra hand-like geometry,
- wrong hand-object relationship,
- final hand overlaid with Hunyuan hand.

## Desired pipeline

Input image
→ detection / segmentation
→ inpainting
→ Hunyuan initial candidate
→ Phase 4.2 object-focused refinement
→ object-only candidate extraction
→ object selector
→ Phase 4.3 hand-object alignment refinement
→ scene validator

## Object selector input

The selector should compare object-only candidates:

1. Hunyuan object-only candidate
2. Phase 4.2 refined object candidate
3. optional alternative candidate from prompt/inpaint variation

## Selector score


C_obj =  w1 * completeness+ w2 * 2D object mask fit+ w3 * MoGe depth / point agreement+ w4 * prompt consistency- w5 * fragmentation


## Selector output


selected_object_meshselected_object_poseselected_confidence


## Phase 4.3 responsibility

Phase 4.3 should align the selected object with the hand.

It should optimize:

- object SE(3),
- hand global pose,
- local contact vertices.

It should not globally deform the selected object geometry.

## What to keep from the current post-hoc selector

Keep it as a diagnostic script.

Use it for:

- measuring object completeness,
- showing failure cases,
- creating comparison panels.

Do not treat it as the final pipeline module.  
