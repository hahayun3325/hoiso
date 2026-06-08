# Phase 0.17 — ARCTIC amicuse01 Memory Tradeoff

## Case

`amicuse01`: toy microwave use.

## Observation

The standard setting with `FOHO_FINAL_OCTREE_RES=192` exported selector-stage information but failed before saving final hand/object meshes because of CUDA out-of-memory during final SDF / mesh extraction.

The low-memory setting completed and saved final meshes, but the final object quality degraded/collapsed.

## Important interpretation

This is not a clean final-mesh comparison between octree 192 and octree 128, because the octree-192 run did not produce final object/hand meshes.

The correct interpretation is:

- high-memory/192 setting: better intended extraction quality, but failed on this memory-sensitive case
- low-memory/128 setting: completed successfully, but produced degraded final geometry

## Why it matters

This supports the need for a robust object-selection and fallback strategy:

1. Preserve the best object candidate before final extraction.
2. Detect when final extraction fails or collapses.
3. Fall back to the selected pre-joint object source.
4. Avoid relying only on lower octree resolution as the solution.

## Report wording

`amicuse01` is a memory-sensitive failure case. Reducing the memory setting avoids OOM but can harm object quality, showing that memory fallback alone is not enough. A better solution is confidence-guided object preservation plus contact-aware pose refinement.
