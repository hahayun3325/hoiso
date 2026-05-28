# Smoke 019 — Root Cause and Solution Direction

## Root cause

Smoke 019 localizes the fragmented object mesh issue to the final guided object latent/SDF/FlexiCubes extraction stage.

The object is already fragmented in:

`debug_obj_before_hunyuan2moge.ply`

Therefore, the fragmentation happens before:

- Hunyuan-to-MoGe transform
- final RT / scale transform
- `src/foho/guidance/run.py` post-processing
- final export

## Evidence

smoke015_hunyuan_initial:1 component, fragmentation_score = 0.000000smoke019_before_h2m:112 components, fragmentation_score = 111.528852smoke019_exported_obj:6 components, fragmentation_score = 5.514633

## Interpretation

The structured prompt creates a good inpainted object and a good Hunyuan initial mesh.

However, final Hunyuan guidance damages the object latent/SDF and extracts a fragmented object mesh.

## Most likely mechanism

The final guidance optimizes object prediction/noise using image-space losses such as normal, depth, silhouette, and contact-related terms.

Under low-step and partial-observation settings, this may preserve visible/contact-supported fragments while losing global object completeness.

## Solution direction

The first fix to test is object-preserving guidance:

- freeze object noise / latent updates,
- optimize only object pose, scale, and translation,
- keep hand/contact optimization active,
- use object-completeness score to decide whether to trust final object or fallback to an earlier-stage object.

## HOLDSE-Flow implication

A later stage is not always better.

HOLDSE-Flow should include:

- structured object prompting
- object completeness checking
- semantic drift diagnosis
- 2D–3D consistency verification
- confidence-guided fallback
- object-preserving contact refinement  
