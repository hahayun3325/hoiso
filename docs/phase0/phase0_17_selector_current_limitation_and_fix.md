# Phase 0.17 — Selector Limitation and Correct Fix

## Current problem

The current post-hoc selector and mock selector are useful for diagnosis, but they are not yet the final selector design.

The main issue is candidate construction.

In several OakInk split000 panels, the selector chooses `hunyuan_rank0`. Visually, this candidate can still include both hand and object, because it is extracted from the full Hunyuan HOI mesh by connected-component rank.

This means `hunyuan_rank0` is not guaranteed to be an object-only candidate.

## Why this happens

The selector currently scores simple mesh completeness:

- number of connected components
- largest face ratio
- fragmentation score
- watertightness

A merged hand-object mesh can still have:

- one connected component
- low fragmentation score
- many faces

So the selector may incorrectly prefer it.

## Correct selector input

The selector after Phase 4.2 should compare object-only candidates:

1. object candidate before joint alignment:
   `phase42_obj_transformed_before_joint_*.ply`

2. final guided object candidate:
   `guidance_out/*obj*.ply`

3. optional earlier trusted object-only candidate, if it is truly object-only.

It should not compare:

- full Hunyuan HOI mesh
- largest connected Hunyuan component if it contains hand and object

## Correct selector location

The selector should be inserted after object-only optimization and before joint hand-object alignment.

Conceptual location:

Object-focused refinement
→ export / score object-only candidates
→ selector chooses reliable object geometry + pose
→ joint hand-object alignment uses selected object

## Current conclusion

The current panels show why the selector is needed, but they do not yet prove a fully integrated selector.

The next implementation step is to replace the post-hoc Hunyuan-rank candidate selector with an internal object-only selector between Phase 4.2 and Phase 4.3.  
