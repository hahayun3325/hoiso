# alapuse01 — Gate D-0 fit v1a final decision

## Decision

Gate D-0 fit v1a hand-frame diagnostic: FAIL_SIMPLE_AXIS_FLIPS.

## Evidence

The best simple transform is flip_yz, but it still does not produce the desired hand-lid interaction.

Numerically, flip_yz is closest among the tested transforms, but the hand is also very close to the fitted base:

- hand-to-fitted-lid within 20 mm: 12 vertices
- hand-to-fitted-base within 20 mm: 60 vertices

Visually, none of the candidate hand transforms places the right fingers correctly on the lid/screen.

## Interpretation

The issue is not only a simple axis convention problem.

The exact FMH shared-frame transform is missing. We need to recover the transform that previously placed the reconstructed hand and laptop in the same aligned scene.

## Decision boundary

Do not run Gate C or sandbox optimization from fit_v1/v1a.

Do not use simple axis flips as the final hand-object frame.

## Next step

Recover the previous working aligned frame or the exact h2m/m2h/FMH hand-to-image transform, then rerun the fitter in that shared frame.
