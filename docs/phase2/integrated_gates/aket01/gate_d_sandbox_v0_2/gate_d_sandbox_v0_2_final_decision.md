# aket01 Gate D sandbox v0.2 final decision

## Decision

FAIL_SIGNED_COLLISION_DEEP_INTERSECTION_AS_IMPLEMENTED.

## Evidence

The signed-distance audit ran successfully with igl.signed_distance.

Reported values:

- decision = FAIL_SIGNED_COLLISION_DEEP_INTERSECTION
- min signed distance ≈ -0.117 m
- negative_count_lt_0 = 398
- negative_count_lt_minus_002 = 374
- negative_count_lt_minus_005 = 350
- negative_ratio_lt_minus_002 ≈ 0.48
- negative_ratio_lt_minus_005 ≈ 0.45

## Interpretation

The visually plausible hand-body contact is not sufficient evidence of physical validity.
The v0.1 unsigned proxy could not distinguish surface contact from penetration.

## Important limitation

The object body mesh may be open or non-watertight. Signed distance can be unreliable on such meshes.
Therefore, before running a collision correction, run a v0.2a SDF sanity / mesh watertightness audit.

## Next step

Run v0.2a SDF sanity audit.
