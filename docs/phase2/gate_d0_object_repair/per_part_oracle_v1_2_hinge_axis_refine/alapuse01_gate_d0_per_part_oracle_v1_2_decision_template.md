# alapuse01 — Gate D-0 per-part oracle v1.2 hinge-axis refinement decision

## Decision

Fill after visual inspection.

## What v1.2 tests

V1.2 refines v1.1 by searching:

- multiple hinge-axis candidates
- multiple hinge-center offsets
- multiple screen hinge angles
- pseudo GT base/screen assignment
- collapse-safe scoring

## PASS if

- collapse_flag = false
- bbox volume ratio remains close to 1
- screen/base visually align better than v1.1
- hinge remains connected
- symmetric metric improves or stays acceptable
- contact surface becomes reliable enough for Gate C v3

## PARTIAL PASS if

- scale is good and no collapse
- but screen/base are still visually misaligned
- hinge axis is still weak

## FAIL if

- object collapses
- bbox becomes much worse
- screen/base disconnect badly
- metrics become much worse than v1.1

## Next step

If PASS:
- run Gate C v3 contact verification in the repaired frame.

If PARTIAL PASS:
- implement v1.3 with better pseudo-GT part split or image/silhouette scoring.

If FAIL:
- inspect Gate A part quality and rebuild part meshes.
