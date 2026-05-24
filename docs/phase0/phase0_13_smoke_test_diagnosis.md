# Phase 0.13 — Smoke Test Diagnosis

## Current status

Phase 0.13 is a partial pass.

The pipeline now reaches all major stages:

- preprocessing
- inpainting
- MoGe
- Hunyuan3D
- HaMeR / MANO alignment
- guidance / optimization

## Current blocker

The remaining blocker is CUDA out-of-memory during late guidance / optimization.

## Evidence

The smoke_006 run produced:

- masks and cropped images
- inpainted object image
- MoGe depth/normal/mesh/point cloud
- Hunyuan HOI mesh
- HaMeR output
- aligned MANO mesh
- guidance debug renderings and intermediate hand/object meshes

The final error is CUDA OOM while processing `test_inpainted_object.png`.

## Next action

Create a low-memory guidance run by:

- splitting stages or reusing existing artifacts
- reducing final optimization / guidance steps
- reducing render resolution
- adding explicit CUDA cleanup between heavy stages
