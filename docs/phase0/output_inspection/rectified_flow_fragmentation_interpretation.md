# Rectified-Flow Fragmentation Interpretation

## Root area

The object fragmentation happens during final guided latent/SDF/FlexiCubes extraction.

It is not mainly caused by:

- final rendering,
- bbox alignment,
- Hunyuan-to-MoGe transform,
- final RT/scale transform,
- final export.

## Interpretation

The final rectified-flow guidance appears to preserve partial visible/contact-supported cues while losing global object completeness.

## Why this can happen

The object is heavily occluded.

2D losses such as mask, depth, normal, and silhouette mainly supervise visible regions.

Without a strong object-completeness or shape-preservation constraint, final guidance can overfit partial evidence.

## Reduced-setting effect

Reduced inference steps and low-memory settings may amplify the issue, but they are not the only cause.

Evidence:

- increasing octree resolution did not restore completeness,
- freezing object noise did not restore completeness,
- freezing object pose did not restore completeness.

## Design implication

Use rectified-flow guidance for pose/contact only when object completeness is protected.

Do not blindly trust the final guided object mesh.
