# alapuse01 — Gate D-0 fit v1a6 final decision

## Decision

HAND_SCALE_PROVENANCE_SUSPECT_ALIGNED_MANO.

## Evidence

v1a6 reports:

- aligned_mano_xy_over_guidance_hand_xy = 3.0903
- aligned_mano_max_over_guidance_hand_max = 3.0903
- guidance_hand_xy_over_active_object_xy = 0.6610
- aligned_mano_xy_over_active_object_xy = 2.0426
- h2m scale from determinant = 0.3168

## Interpretation

The oversized-hand issue is mainly from aligned_mano, not from guidance_hand.

guidance_hand is at a plausible scale relative to the laptop. aligned_mano is about 3x larger than guidance_hand.

h2m also contains a strong scale term, so it should not be blindly applied on top of aligned_mano without checking for double scaling.

## Decision boundary

Do not use raw aligned_mano as the hand seed.

Do not run full v1b yet.

## Next step

Run v1a7 corrected-scale root-pose probe:

1. rescale aligned_mano to guidance_hand bbox scale,
2. scale the laptop object using v1a5 object_scale_to_depth_xy,
3. test a small root/contact closing translation,
4. inspect whether the corrected frame supports lid/screen contact.
