# Phase 0.17 — Native Renderer vs Custom Panel Renderer

## Observation

The pipeline-saved native debug renderings look more reliable than custom `.ply` renderings.

The native images include:

- `rendered_obj_normal_t*_opt*.png`
- `rendered_normal_t*.png`
- `rendered_normal_hand_t*_opt*.png`

These are produced inside the optimization loop with the same PyTorch3D camera, FOV, rasterizer, and MoGe normal target used by the guidance losses.

## Why custom panels look wrong

The custom panels load exported `.ply` files and render them with matplotlib or trimesh.

Those renderers do not know the original:

- camera intrinsics / FOV
- image size
- MoGe coordinate frame
- PyTorch3D projection convention
- hand-object optimization frame

Therefore, object candidates can look twisted, flat, or blob-like even when the selector logic is correct.

## Interpretation

The selector should be verified by:

1. log messages,
2. md5 checks,
3. fragmentation scores,
4. native pipeline renderings.

Custom `.ply` panels should be used only for qualitative inspection, not as strong evidence of camera alignment.

## Report recommendation

Use native renderings to show pipeline alignment.

Use custom selector panels only to show:

- before Phase 4.2 candidate,
- after Phase 4.2 candidate,
- selected candidate,
- fragmentation score,
- md5 verification.
