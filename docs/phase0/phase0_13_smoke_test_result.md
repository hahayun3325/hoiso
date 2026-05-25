# Phase 0.13 — Near-Complete Smoke Test

## Status

Phase 0.13 is a near-complete partial pass.

The pipeline reaches the final guidance / optimization stage, but the final guidance meshes are still missing:

- `guidance_out/test_obj.ply`
- `guidance_out/test_hand.ply`

## Best run so far

Run folder:

~/foho_phase0/runs/smoke_007

Main allocator change:

export PYTORCH_CUDA_ALLOC_CONF="backend:cudaMallocAsync"

## What passed

The run successfully produced:

- Gemini object response
- cropped HOI images
- object and hand masks
- inpainted object image
- MoGe mesh/depth/normal outputs
- Hunyuan HOI mesh
- HaMeR hand mesh
- aligned MANO mesh
- guidance debug folder and optimization logs

## Current blocker

The final guidance stage still fails with device allocation / memory pressure. Final meshes are not saved.

## Current assessment

The main remaining bottleneck is memory pressure inside the guidance subprocess.  
