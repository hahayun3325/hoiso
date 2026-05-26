# Prompt and Related Work Observations

## Current failure

The smoke_013 output shows plausible hand-object alignment, but the object shape drifts from a rectangular SPAM tin to a generic rounded can.

## Diagnosis

The Gemini response was category-correct but geometrically vague:

A can of Spam.

This may have encouraged the inpainting and 3D generation stages to follow a generic can prior.

## Prompt ablation hypothesis

A structured object description prompt may reduce semantic drift by forcing the object description to include:

- category
- brand/text
- visible shape
- flat vs round surfaces
- silhouette
- edges/corners
- negative constraints

Example:

A rectangular SPAM canned meat tin with flat front and back faces, rounded rectangular corners, and a metal top. The object is boxy and not a cylindrical soda can or soup can.

## Related work connections

### ForeHOI

ForeHOI suggests that separated 2D inpainting and 3D completion can accumulate errors. Its joint 2D mask inpainting and 3D shape completion is directly relevant to semantic drift.

### WHOLE

WHOLE shows that reconstruction can be guided by object masks, contact cues, hand joints, interaction terms, and temporal smoothness. This supports using contact and mask consistency as guidance.

### ArtHOI

ArtHOI shows that structured MLLM prompting can improve contact reasoning. This supports using structured prompts and validation rules instead of vague object descriptions.

## Proposal implication

The proposed HOLDSE-Flow direction should include:

- semantic drift detection
- structured object description
- 2D-3D silhouette verification
- contact confidence estimation
- confidence-guided coordination
- contact-aware physical refinement  
