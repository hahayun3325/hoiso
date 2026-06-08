# Phase 0.17 — ARCTIC amicuse01 Low-Memory Rerun

## Problem

The first `amicuse01` selector-native v2 run exported selector candidates but failed before saving the final hand/object meshes.

The failure occurred during final SDF / VAE decoding and mesh extraction with a CUDA out-of-memory error.

## Cause

`amicuse01` is a harder reconstruction case than the other ARCTIC samples.

The object is a toy microwave with a box body, open door, handle, and large flat surfaces. The selector diagnostics showed very high fragmentation scores, above 100 components/fragments, which made final latent/SDF decoding more memory intensive.

This was not caused by a different input image resolution. It was caused by the object complexity, fragmentation, and final mesh extraction memory peak.

## Fix

The low-memory rerun used:

- `FOHO_FINAL_OCTREE_RES=128`
- `FOHO_NUM_INFERENCE_STEPS=5`
- `FOHO_OPT_STEPS_JOINT=3`
- `FOHO_SIL_FACES_PER_PIXEL=2`

The rerun completed successfully and saved:

- `guidance_out/amicuse01_hand.ply`
- `guidance_out/amicuse01_obj.ply`

## Interpretation

For Phase 0.17, `amicuse01` should be reported as a memory-sensitive case.

The result is useful for qualitative analysis, but it was produced under lower final extraction resolution than the other cases.
