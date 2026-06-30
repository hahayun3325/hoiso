# alapuse01 — Gate D-0 v1.3 kinematic-chain oracle

## Decision

Proceed to v1.3 kinematic-chain oracle, not Gate C v3.

## Reason

V1.2 improves numeric alignment and avoids collapse, but the screen/base/hinge are still visually inconsistent and physically penetrating.

The problem is not only scoring. It is model parameterization.

## V1.3 target

Use a laptop kinematic model:

- one shared global scale
- keyboard_base as root SE(3)
- screen/top_lid rotates around one hinge axis
- no independent screen translation
- no independent per-part scale
- hinge connectivity penalty
- screen/base interpenetration penalty
- symmetric geometry metrics only as evaluation/reporting

## Success condition

V1.3 passes only if:

- collapse_flag = false
- bbox volume ratio remains reasonable
- screen/base are visually connected
- screen/base do not visibly penetrate
- repaired object frame is reliable enough for Gate C v3

## If v1.3 passes

Run Gate C v3 contact verification in the repaired frame.

## If v1.3 fails

Move toward silhouette/depth/image-based scoring and inspect Gate A part quality.
