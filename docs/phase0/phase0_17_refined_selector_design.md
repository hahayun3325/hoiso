# Phase 0.17 — Refined Selector Design

## Current post-hoc selector

The current selector is useful for diagnosis.

It compares object candidates using object completeness:

- connected components,
- largest-face ratio,
- fragmentation score.

However, it is not yet a complete final pipeline module.

## Current limitation

When the selector chooses the Hunyuan initial mesh, it may choose a full HOI mesh rather than an object-only mesh.

This can cause:

- extra Hunyuan hand geometry,
- final hand overlaid with Hunyuan hand,
- wrong front/back relationship,
- poor contact alignment.

## Better pipeline placement

### Stage A — after Phase 4.2

Run an object selector after object-focused rectified-flow refinement.

The selector should choose the best object-only candidate.

Inputs:

- Hunyuan object candidate,
- Phase 4.2 refined object,
- optional inpaint/Hunyuan alternatives.

Score:

C_obj = completeness + 2D mask fit + MoGe point agreement + prompt consistency - fragmentation

Output:


selected object geometry + selected object pose


### Stage B — Phase 4.3

Run contact-aware alignment refinement.

Freeze or strongly regularize object geometry.

Optimize:

- object SE(3),
- hand global pose,
- selected contact fingers or hand vertices.

Do not globally deform the object.

### Stage C — after Phase 4.3

Run a scene validator.

Score:


C_scene = object quality + hand-object contact + low penetration + rendered mask fit + depth/front-back consistency


If the scene fails, do not simply replace the object. Instead:

- rerun local alignment,
- reduce contact loss,
- roll back to Phase 4.2 selected object and re-optimize,
- or mark the sample as low confidence.

## Main principle

Object selection and hand-object alignment are related but not identical.

The selector should choose a reliable object.

The following optimization stage should align it with the hand.

The final validator should check whether the full scene is correct.  
