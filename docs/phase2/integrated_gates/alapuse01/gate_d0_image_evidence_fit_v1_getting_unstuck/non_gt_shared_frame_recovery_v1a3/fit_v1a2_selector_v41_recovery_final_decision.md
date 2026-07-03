# alapuse01 — Gate D-0 fit v1a2 selector-v41 frame recovery final decision

## Decision

OPTION_B_GT_ORACLE_ONLY.

## Evidence

The selector-v41 aligned scene was generated using GT files:

- `gt_reference/selected/gt_right_hand_points.ply`
- `gt_reference/selected/gt_object_mesh.ply`

The helper script computes a hand-based Umeyama similarity transform:

- source: predicted selector-v41 hand
- target: GT hand vertices

Therefore, the visually good selector-v41 aligned scene is a GT/oracle diagnostic scene.

## Interpretation

This scene is useful for understanding the desired hand-lid/screen contact, but it cannot be used as the final non-GT shared-frame seed.

## Next step

Recover a non-GT approximation by replaying FMH/H2M transform candidates from the selector-v41 run:

- guidance hand
- guidance object
- aligned MANO
- h2m transform
- inverse h2m transform
- active clean parts
- image-derived lid/base masks and contact prior
