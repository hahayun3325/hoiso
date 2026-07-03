# alapuse01 — Gate D-0 fit v1a7 final decision

## Decision

PARTIAL / FULL_ROOT_SNAP_TOO_LARGE_SCALE_FIX_NOT_ENOUGH.

## Evidence

v1a7 corrected two important scale issues:

- aligned_mano was rescaled to guidance_hand bbox scale.
- active object was scaled by v1a5 object_scale_to_depth_xy.

However:

- A_scaled_hand_scaled_object_no_translation: hand still floats far above lid.
- D_scaled_hand_scaled_object_clipped_8cm_root: 8 cm correction is not enough.
- B_scaled_hand_scaled_object_full_root_snap_debug: best visual contact, but requires about 0.419 m translation.
- C_scaled_hand_scaled_object_axis_only_snap_debug: moves closer but still does not make valid contact.

## Interpretation

Scale correction is necessary but not sufficient.

The remaining issue is a large root-pose / shared-frame mismatch.
This should not be solved by a free 42 cm snap, because that would hide the upstream transform error.

## Decision boundary

Do not run v1b yet.
Do not use B full-root snap as final seed.
Use B only as a debug upper-bound showing the desired contact geometry.

## Next step

Run v1a8 transform-chain root-pose provenance audit.
