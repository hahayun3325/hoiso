# alapuse01 — Gate D-0 fit v1a8 final decision

## Decision

PASS_DIAGNOSTIC_ROOT_CAUSE_IDENTIFIED.

## Evidence

v1a8 shows:

- A_v1a7_scaled_no_translation: hand floats above object.
- B_hand_scaled_to_guidance_hand_center: strong improvement, but visual contact may still land near keyboard/base.
- C_object_scaled_to_guidance_obj_center: no meaningful improvement.
- D_both_scaled_to_guidance_centers: similar to B, so improvement comes from hand-root correction.
- E_raw_guidance_hand_with_active_parts: coherent but contacts wrong region.

Root deltas:

- delta_hand_scaled_to_guidance_hand_norm = 0.974 m
- delta_object_scaled_to_guidance_obj_norm = 0.0165 m

## Interpretation

The main root-pose issue is in the hand branch.

The corrected-scale aligned_mano hand lost its correct root translation.
The object branch is not meaningfully root-misaligned.

## Decision boundary

Do not run full v1b optimization yet.

First build v1b0:

- corrected-scale aligned_mano hand shape
- guidance_hand root translation
- corrected-scale object
- no extra object-root correction

Then audit whether contact lands on lid/screen or still on keyboard/base.

## Next step

v1b0 corrected hand-root seed + semantic contact audit.
