# Smoke 021 — Verified Freeze Object-Noise Ablation

## Goal

Verify whether freezing object-noise learning rates prevents final object fragmentation.

## Verified setting

The run explicitly used:

FOHO_NOISE_OBJ_LR1=0.0
FOHO_NOISE_OBJ_LR2=0.0

the log printed:

`[FOHO_DEBUG] noise_obj_lr1=0.0, noise_obj_lr2=0.0`

## Result

The run completed and produced final hand/object meshes.

However, the object remained fragmented.

## Evidence

smoke015_hunyuan_initial:1 component, fragmentation_score = 0.000000smoke019_exported_obj:6 components, fragmentation_score = 5.514633smoke020_exported_obj:4 components, fragmentation_score = 3.458513smoke021_exported_obj:4 components, fragmentation_score = 3.458513

## Interpretation

Freezing object-noise learning rates is not sufficient.

The object fragmentation is likely caused by the final guided latent/SDF/FlexiCubes extraction path, not only by late object-noise optimization.

## Next direction

Use confidence-guided object source fallback and object-preserving contact refinement:

- keep the best earlier object shape,
- reject fragmented final object meshes,
- use final guidance mainly for hand/contact alignment,
- optimize object pose/contact without changing global object geometry.  
