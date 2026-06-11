# Phase 0.17 — ARCTIC True Predicted 3D Mesh Overlay Blockers

## Current status

The current ARCTIC report assets include GT 2D overlays and surface-sampled 3D metrics.

They do not yet include true predicted 3D mesh overlays on the RGB image.

## Why not yet

A true overlay requires a complete transform chain:

1. Take the predicted hand/object mesh from FollowMyHold output space.
2. Apply the exact similarity transform used in metric evaluation to align prediction to ARCTIC camera-space GT.
3. Project the aligned 3D vertices using the correct ARCTIC camera intrinsics for the selected view.
4. Apply the official ARCTIC crop transform to map original image coordinates to the 1000×1000 crop.
5. Rasterize/render the mesh with visibility and occlusion handling.

## Why the current metrics are still valid

The current metrics do not rely on 2D overlay positions.

They are computed from:

- GT 3D camera-space object vertices
- GT 3D camera-space hand vertices
- aligned predicted 3D meshes
- surface-sampled CD/F5/F10

The 2D overlay is only a sanity check for frame/view/crop correctness.

## Future task

Build an aligned-mesh projection renderer for qualitative visualization.
