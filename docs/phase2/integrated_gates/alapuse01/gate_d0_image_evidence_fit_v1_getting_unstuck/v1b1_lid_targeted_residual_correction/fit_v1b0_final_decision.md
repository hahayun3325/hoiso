# alapuse01 — Gate D-0 fit v1b0 final decision

## Decision

SEMANTIC_CONTACT_FAIL_REMAINS.

## Evidence

v1b0 fixed the large hand root-frame gap:

- hand no longer floats
- corrected-scale aligned_mano hand was re-rooted to guidance_hand

However, the contact is still semantically wrong:

- red/base markers dominate the physical contact region
- blue/lid markers are near fingers but do not define the real contact
- hand_to_lid_semantic has no vertices within 5 cm
- hand_to_base_semantic has many vertices within 5 cm

## Interpretation

v1b0 validates the hand-root correction, but it does not produce correct lid/screen contact.

## Decision boundary

Do not run full v1b optimization.
Do not run sandbox Gate D.

## Next step

Run v1b1 lid-targeted residual correction diagnostic.
