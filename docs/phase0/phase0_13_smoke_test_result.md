# Phase 0.13 — First Completed Low-Memory Smoke Test

## Status

Phase 0.13 passed as a low-memory smoke test.

The pipeline produced the final guidance meshes:

- `guidance_out/test_obj.ply`
- `guidance_out/test_hand.ply`

## Successful run

Run folder:

`~/foho_phase0/runs/smoke_013_octree192_guidance`

## Key fix

The main memory bottleneck was final Hunyuan guidance mesh extraction.

The original final extraction used:

`octree_res = 384`

This caused CUDA OOM during:

`flexi.construct_voxel_grid(octree_res)`

The successful smoke run used:

`export FOHO_FINAL_OCTREE_RES=192`

## Low-memory settings

export PYTORCH_CUDA_ALLOC_CONF="backend:cudaMallocAsync"
export FOHO_RENDER_SCALE=1.0
export FOHO_RENDER_FACES_PER_PIXEL=1
export FOHO_SIL_FACES_PER_PIXEL=5
export FOHO_NUM_INFERENCE_STEPS=8
export FOHO_OPT_STEPS_HAND=40
export FOHO_OPT_STEPS_SCALE=20
export FOHO_OPT_STEPS_JOINT=10
export FOHO_FINAL_OCTREE_RES=192

## Output validation

The final meshes were readable:

- object mesh: non-empty, readable `.ply`
- hand mesh: non-empty, readable `.ply`

## Interpretation

This result verifies that the FollowMyHold pipeline can complete on the local RTX 4090 using low-memory settings.

This is not yet a paper-quality setting. For final evaluation, the original or higher-quality settings should be restored when using a larger GPU or a more memory-efficient mesh extraction strategy.  
