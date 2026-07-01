# alapuse01 — Gate D-0 v1.3 kinematic-chain oracle final judgement

## Decision

Gate D-0 v1.3 kinematic-chain oracle: FAIL / STOP GRID ORACLE LINE.

## Evidence

V1.3 is not visually better than v1.2 and is numerically worse:

- v1.2 symmetric_mean = 0.0320
- v1.3 symmetric_mean = 0.0376
- v1.2 F50 = 0.753
- v1.3 F50 = 0.637
- v1.3 bbox_volume_ratio = 1.503
- v1.3 searched_candidates = 6370
- runtime was around 30 minutes

The visual result still shows disordered screen/base/hinge placement.

## Interpretation

The current oracle-grid approach has reached its limit.

The issue is not only hinge-axis tuning. The deeper issues are:

1. fragmented / unreliable Gate A part meshes
2. GT-Chamfer objective instead of image-evidence objective
3. weak physical validity proxies
4. expensive grid search

## Decision boundary

Allowed:

- v1.3 shows that kinematic constraints are necessary.
- v1.3 shows that post-hoc GT-Chamfer grid search is not the right solver.
- v1.3 supports pivoting toward image-evidence optimization inside FollowMyHold.

Not allowed:

- v1.3 solves laptop pose.
- v1.3 is ready for Gate C v3 contact verification.
- continuing v1.4 grid search is likely to meet the 10-minute target.

## Next step

Stop the oracle-grid line.

Next target:

1. audit/fix Gate A part coherence
2. build a fast image-evidence articulated fitting module
3. integrate Gate A-D variables into FollowMyHold's optimization loop
