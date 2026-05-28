# Smoke 020 — Freeze Object Noise Ablation

## Goal

Test whether freezing object-noise learning rates prevents final object fragmentation.

## Change

The intended change was:

FOHO_NOISE_OBJ_LR1=0.0
FOHO_NOISE_OBJ_LR2=0.0

## Result

Smoke 020 completed and produced final object and hand meshes.

However, the final object remained fragmented.

## Evidence

smoke019_exported_obj:
6 components, fragmentation_score = 5.514633

smoke020_exported_obj:
4 components, fragmentation_score = 3.458513

## Interpretation

The freeze may slightly reduce fragmentation, but it does not solve the problem.

The most likely reason is that the object becomes unstable before or outside the late object-noise optimization being controlled.

## Next direction

A better solution is not only late LR freezing.

The next solutions should test:

1. true early object-shape freeze,
2. object-source fallback to the Hunyuan initial mesh,
3. shape-preservation loss,
4. contact-only local refinement.  
