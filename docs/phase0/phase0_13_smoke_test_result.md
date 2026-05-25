# Phase 0.13 — First Successful Smoke Test

## Status

Phase 0.13 passed if the final guidance meshes exist:

- `guidance_out/test_obj.ply`
- `guidance_out/test_hand.ply`

## Successful run

Run folder:

~/foho_phase0/runs/smoke_007

Main command:

PYTORCH_CUDA_ALLOC_CONF="backend:cudaMallocAsync" \PYTHONPATH=src python3 -m foho.main \  --config configs/pipeline.phase0.env

## Key change

The main change from `smoke_006` to `smoke_007` was switching the PyTorch CUDA allocator backend:

export PYTORCH_CUDA_ALLOC_CONF="backend:cudaMallocAsync"

Earlier runs reached final guidance but failed with CUDA OOM. The async allocator improved memory allocation behavior enough for the smoke test to proceed further.

## Pipeline stages reached

The run reached:

- Gemini object naming
- hand/object preprocessing
- FLUX/Kontext inpainting
- MoGe geometry
- Hunyuan3D HOI mesh generation
- HaMeR hand reconstruction
- H2M and MANO alignment
- final guidance / optimization

## Notes

This smoke test is for setup validation, not final-quality evaluation. For paper-quality results, the original settings and stronger validation should be restored.  
