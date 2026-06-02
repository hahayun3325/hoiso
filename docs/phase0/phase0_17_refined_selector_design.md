# Phase 0.17 — Refined Selector Design  
  
## Main finding  
  
The current post-hoc selector is useful for diagnosis, but it should not be the final pipeline design.  
  
It can identify which object candidate is more complete, but it can still create wrong hand-object alignment when applied after all optimization is finished.  
  
## Why post-hoc replacement is problematic  
  
The post-hoc selector currently combines:  
selected object mesh + final hand mesh
This can fail because:

1. the selected object may come from a different coordinate/pose stage,
2. the selected Hunyuan mesh may be a composite HOI mesh rather than a clean object-only mesh,
3. the final hand may no longer match the selected object,
4. the selector does not optimize contact or front/back relationship.

## Better placement

The selector should be placed between object-focused refinement and final alignment:


Phase 4.2 object-focused rectified-flow refinement→ object selector→ Phase 4.3 hand-object alignment refinement


## Object selector after Phase 4.2

The selector should choose the best object-only candidate.

Candidate sources:

- Hunyuan object candidate,
- Phase 4.2 refined object,
- optional inpainting/Hunyuan alternatives.

The selected candidate should include:


object geometryobject poseconfidence score


The selector should score:


C_obj =  object completeness+ 2D mask fit+ MoGe depth/point agreement+ prompt consistency- fragmentation


## Phase 4.3 alignment refinement

After object selection, Phase 4.3 should refine alignment.

It should preserve or strongly regularize the selected object geometry.

It can optimize:

- object SE(3),
- hand global pose,
- selected hand/contact vertices.

The goal is local alignment refinement, not global object deformation.

## Scene validator after Phase 4.3

The scene validator should check whether the final scene is believable.

It should check:

- contact quality,
- penetration,
- rendered mask consistency,
- depth/front-back consistency,
- hand-object distance.

If the scene fails, do not blindly replace the object. Instead:

- rerun local alignment,
- roll back to the selected Phase 4.2 object,
- reduce aggressive guidance,
- or mark the sample as low confidence.

## Final design principle

The selector should answer:

Which object candidate should the alignment stage trust?

The alignment stage should answer:

How should the hand and selected object be spatially refined?

The final validator should answer:

Is the full hand-object scene believable?

