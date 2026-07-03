# alapuse01 — Gate D-0 fit v1a5 final decision

## Decision

SCALE_MISMATCH_CONFIRMED / NOT_READY_FOR_V1B.

## Evidence

v1a5 reports:

- object_scale_to_depth_xy = 1.4137
- hand_to_active_object_xy_ratio = 2.0426
- scaled_snap_norm_m = 0.1798 m

## Interpretation

The active laptop object is under-scaled relative to MoGe/mask depth.

However, object scaling alone does not resolve the hand-laptop contact relation. After scaling the object to the MoGe/mask XY extent, the hand still floats above the lid and remains visually oversized.

The remaining required snap distance is about 18 cm, which is too large to treat as a small contact refinement.

## Decision boundary

Do not run v1b yet.

Do not claim that object-scale correction solves the case.

## Next step

Run v1a6 hand-scale/provenance audit:

1. compare aligned_mano scale against guidance_hand,
2. inspect h2m transform scale,
3. identify whether the scale bug is from hand branch, object branch, or transform chain.
