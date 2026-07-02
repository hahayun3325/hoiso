# alapuse01 — Gate C v3.3 final decision

## Decision

Gate C v3.3 manual top-lid/screen component verification: FAIL.

## Evidence

The manually selected true top-lid/screen component is far from the verified hand patch:

- top_lid_distance.min = 0.12546 m
- top_lid_distance.mean = 0.20411 m
- within_20mm = 0

The wrong/base-like screen component is much closer:

- nearest_wrong_component_00 mean = 0.00555 m
- within_10mm = 20
- within_20mm = 20

## Interpretation

The current contact target cannot be fixed by more Gate C auditing.

The contact patch is geometrically close to a wrong/base-like fragment, while the true lid is far away.

This means the current object state is wrong. The lid/screen is not where the input image says it should be.

## Decision boundary

Allowed:

- Gate C has diagnosed the failure.
- Contact scorer v0 works mechanically.
- The current object/contact state is not ready for sandbox optimization.

Not allowed:

- The current contact target is a valid screen/top-lid contact.
- The current frame supports the desired input-image contact.
- More nearest-neighbor contact search will solve the problem.

## Next step

Stop Gate C contact-target debugging.

Move upstream to Gate D-0 image-evidence articulated fitting:

- image-derived semantic contact: right hand/fingers touch lid outer surface
- deterministic part relabel using image/mask evidence
- optimize object variables {s, T_base, theta}
- run contact scorer only after the object state is corrected
