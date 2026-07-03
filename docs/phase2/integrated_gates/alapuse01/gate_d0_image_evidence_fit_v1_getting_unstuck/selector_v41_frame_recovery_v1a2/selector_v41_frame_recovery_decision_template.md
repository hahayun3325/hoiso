# alapuse01 — selector-v41 frame recovery decision template

## Goal

Recover the frame where the reconstructed hand plausibly contacts the laptop lid/screen.

## Candidate

`alapuse01_selector_v41_aligned_pred_vs_gt.glb`

Visual observation:
- blue reconstructed laptop appears near the white GT laptop,
- hand/laptop relation appears more consistent with the input image,
- this is better than the old v0 dry-run frame.

## Key caution

This scene is stored under `gt_reference`, so it may use GT alignment.

Before using it for v1b, classify it:

### Option A — non-GT usable shared frame

Use this if the transform is produced from FMH outputs only:
- h2m transform,
- hand alignment,
- image/MoGe frame,
- selector-v41 pipeline outputs.

Then v1b can use this as the active shared-frame seed.

### Option B — GT/oracle diagnostic only

Use this if the transform uses GT object/hand alignment:
- GT object mesh,
- GT hand mesh,
- Procrustes/Umeyama to GT.

Then it is useful for debugging and upper-bound analysis, but not allowed as a final method seed.

## Next implementation after classification

If Option A:
  create fit_v1b_selector_v41_shared_frame.py.

If Option B:
  create a non-GT approximation by replaying the FMH h2m / hand-to-image transform chain from the selector-v41 run.
