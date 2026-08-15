# Preregistration: first post-lineage Gate-C branch

Case: `alapuse02v3n60`

## Preconditions

- [ ] H0 raw saved vertices → raw saved `pred_keypoints_3d`: PASS
- [ ] H1 handedness-adjusted joints → saved guidance 3D joints: PASS
- [ ] H2 saved guidance 3D → saved guidance 2D: PASS
- [ ] H3 source joints → exact C1/shared frame: PASS
- [ ] H4a ordered source vertices → serialized zero-update MANO mesh: PASS
- [ ] H4b zero-update mesh-derived joints → source joints: PASS
- [ ] Correct physical upper-hand candidate is source-verified
- [ ] Laptop, camera, hinge, and target hashes frozen

## Hypothesis

A source-correct upper-hand candidate can satisfy the target-frame hand evidence using bounded global root correction and only the Gate-B active-finger articulation.

## Trainable variables

- hand-root translation
- hand-root axis-angle correction
- Gate-B active-finger MANO joints

## Frozen variables

- MANO shape and scale
- non-active fingers initially
- hand topology
- camera and raster
- complete laptop geometry
- lid/base relation and hinge state

## Pre-registered bounds

- root rotation delta: <= 10 degrees per axis
- active-finger delta: <= 15 degrees per axis for the first trial
- translation radius: no larger than Branch E

## Loss schedule

1. source-faithful 2D keypoint reprojection
2. hand silhouette/image anchor
3. strong initial-pose prior
4. joint-limit regularization
5. weak lid-preference diagnostic only after projection passes

Contact attraction and collision remain disabled until the projection gate passes.

## Acceptance

- normalized RMSE <= 0.50
- normalized p95 <= 0.75
- trust fraction < 0.98
- proper/chirality-consistent solution
- hand silhouette non-regression
- correct upper-hand identity
- screen/lid part preference
- finite depth and projection
- all parameter bounds satisfied
- laptop and camera hashes unchanged

## Stop rule

One bounded trial. If it fails, do not silently expand the degrees of freedom. Choose either a whole-laptop similarity diagnostic or contained-failure closure as a separate preregistered branch.
