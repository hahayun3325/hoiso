# alapuse01 — Gate D-0 v1.3 kinematic-chain oracle decision

## Decision

Fill after visual inspection.

## What v1.3 tests

V1.3 asks whether a physically constrained laptop model can repair the object frame better than free part motion.

Model:

- one shared global scale
- keyboard_base root SE(3)
- screen rotates around one hinge axis
- no independent screen translation
- no independent per-part scale
- physical overlap/crossing proxies in scoring

## PASS if

- collapse_flag = false
- bbox volume ratio is reasonable
- screen/base are visually connected
- screen/base do not visibly penetrate
- physical proxy flags are acceptable
- repaired frame is reliable enough for Gate C v3

## PARTIAL PASS if

- scale and no-collapse are good
- but visual alignment or physical validity remains imperfect

## FAIL if

- object collapses
- screen/base still cross badly
- physical proxy flags are bad
- visual result is not a laptop

## Next step

If PASS:
- run Gate C v3 contact verification in this repaired frame.

If PARTIAL PASS:
- compare with v1.2 and decide between template/CAD oracle or silhouette/depth scoring.

If FAIL:
- inspect Gate A part quality and consider controlled articulated asset/template.
