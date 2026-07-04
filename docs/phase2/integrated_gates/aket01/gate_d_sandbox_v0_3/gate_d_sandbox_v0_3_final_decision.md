# aket01 Gate D sandbox v0.3 final decision

## Decision

PASS_PROXY_PUSHOUT_REDUCES_COLLISION_KEEP_CONTACT.

## Evidence

The proxy collision push-out selected alpha = 1.0.

Reported values:

- translation_norm ≈ 0.0331 m
- deep proxy penetration count reduced from 350 to 145
- within_05 contact count changed from 593 to 531

## Interpretation

The v0.3 proxy correction substantially reduces the collision proxy while preserving most of the hand-object contact.

This is a successful sandbox result for the positive-control case.

## Important limitation

This is not a final physical collision proof.

The body mesh is not watertight, so raw signed-distance depth is unreliable. v0.3 is therefore correctly treated as a robust proxy-collision repair, not a final SDF-based optimizer.

## Next step

Package aket01 as the positive-control result, then move to abox01 for a stronger penetration-repair showcase.
