# alapuse01 — standalone fitter v0.1 reject decision

## Decision

Reject v0.1 conservative optimizer output.

Keep the v0 dry-run frame / active clean parts as the active seed.

## Evidence

V0 dry-run loaded active parts, current object, and current hand in a sensible shared frame.

V0.1 selected a hinge rotation of -18 degrees. Visual inspection shows the laptop pose moves away from the good dry-run alignment.

## Interpretation

The v0.1 physical proxy is too weak. It rewards local hinge proximity but does not preserve image/object/hand alignment.

## Do not use

Do not use:

- screen_v0_1_hinge_adjusted.ply
- object_v0_1_conservative_union.ply

as the active repaired object.

## Active seed

Use the v0 active clean parts:

- active_clean_parts/screen.ply
- active_clean_parts/keyboard_base.ply
- active_clean_parts/hinge.ply

with the current guidance hand/object frame.

## Next step

Move to Gate C v3-lite contact verification using the v0 active seed.

Do not return to Gate A v2 unless Gate C v3-lite fails because the screen geometry is too broken.
