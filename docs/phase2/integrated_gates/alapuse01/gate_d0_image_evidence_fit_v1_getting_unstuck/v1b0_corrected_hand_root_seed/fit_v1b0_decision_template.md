# alapuse01 — Gate D-0 fit v1b0 corrected hand-root seed decision

## Input

v1b0 uses:

- corrected-scale aligned_mano hand shape from v1a7,
- guidance_hand root translation from v1a8,
- corrected-scale object parts from v1a7,
- no extra object-root correction.

## Visuals to inspect

- v1b0_corrected_hand_root_seed.glb
- v1b0_semantic_contact_audit_blue_lid_red_base.glb

## Decision rule

If the hand now contacts the lid/screen:
  PASS_TO_V1B1_SMALL_RESIDUAL_FITTER.

If the hand still contacts keyboard/base:
  SEMANTIC_CONTACT_FAIL_REMAINS.
  Do not run full v1b.
  Next step should be lid-targeted residual correction using image evidence.

If the hand floats:
  ROOT_FIX_INSUFFICIENT.
  Return to transform-chain inspection.

## Final decision

TODO after visual inspection.
