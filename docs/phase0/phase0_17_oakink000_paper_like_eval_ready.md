# Phase 0.17 — OakInk split000 Paper-Like Evaluation Ready

## Status

OakInk split000 now has verified image-level GT annotations:

- image: `south_east_color_90.png`
- selected annotation view id: `1`
- GT hand vertices: `hand_v.pkl`
- GT hand joints: `hand_j.pkl`
- camera intrinsics: `cam_intr.pkl`
- object transform: `obj_transf.pkl`
- object mesh: `A01023.obj`

## Official repo verification

The official OakInk repo confirms the view-name ordering:

- `view_id=0`: `north_east_color`
- `view_id=1`: `south_east_color`
- `view_id=2`: `north_west_color`
- `view_id=3`: `south_west_color`

The official docs also state:

- `hand_v` and `hand_j` are in camera space
- `obj_transf` is `T_c_o`, from object canonical space to camera space
- `cam_intr` is the camera intrinsic matrix

## Evaluation

For one-sample paper-like evaluation, we compute:

1. Align predicted hand mesh to GT hand vertices using similarity transform.
2. Apply the same transform to predicted object mesh.
3. Compare transformed predicted object with GT object mesh transformed by `T_c_o`.
4. Report CD, F5, F10, object fragmentation, and hand alignment RMSE.

## Caution

This is paper-like and follows the core protocol, but it is still a one-sample diagnostic evaluation. It should not be presented as a full official benchmark table until the evaluator is validated across more samples.
