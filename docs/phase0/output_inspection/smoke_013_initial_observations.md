# Phase 0.14 — Initial Output Inspection

## Run

smoke_013_octree192_guidance

## Current status

The pipeline completed end-to-end under low-memory settings.

## Successful outputs

- final object mesh exists
- final hand mesh exists
- meshes are readable and non-empty

## Key low-memory fix

FOHO_FINAL_OCTREE_RES=192

## Expected quality limitations

### Reduced guidance / optimization steps

Potential effects:

- weaker hand alignment
- weaker object refinement
- less stable hand-object relation
- noisier contact

### Reduced octree resolution

Potential effects:

- coarser geometry
- weaker thin structures
- weaker sharp boundaries
- reduced surface detail
- less precise contact geometry

## Key research direction

Investigate whether contact-aware supervision and confidence-guided coordination can recover interaction quality despite lower-memory upstream reconstruction quality.

## Inspection checklist

- [ ] object completeness
- [ ] object smoothness
- [ ] hand pose plausibility
- [ ] hand-object penetration
- [ ] floating contact
- [ ] segmentation quality
- [ ] detector quality
- [ ] MoGe consistency
- [ ] contact realism
- [ ] geometry artifacts  
