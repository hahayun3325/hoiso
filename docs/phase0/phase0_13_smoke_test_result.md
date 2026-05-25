# Phase 0.13 — Near-Complete Smoke Test

## Status

Phase 0.13 is a near-complete partial pass.

The pipeline reaches final Hunyuan guidance / optimization, but final guidance meshes are still missing:

- `guidance_out/test_obj.ply`
- `guidance_out/test_hand.ply`

## Best status so far

The previous resolution mismatch was fixed by keeping render resolution consistent:

export FOHO_RENDER_SCALE=1.0

This avoids the 256-vs-512 tensor mismatch between renderer outputs and MoGe/mask tensors.

## Current blocker

The current blocker is still CUDA memory pressure, now occurring during voxel-grid / FlexiCubes mesh extraction:

flexi.construct_voxel_grid(octree_res)
torch.OutOfMemoryError: Allocation on device

## Current interpretation

The final guidance stage is too memory-heavy for the current RTX 4090 setup under current settings. The next step is to reduce guidance steps and investigate lowering mesh extraction resolution / octree resolution.  
