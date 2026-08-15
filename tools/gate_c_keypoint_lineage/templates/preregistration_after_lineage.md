# Preregistration: first branch after Gate-C lineage identity

Status: `NOT_AUTHORIZED_UNTIL_H0_H4_PASS`

## Frozen inputs

- exact target RGB and raster:
- selected HaMeR batch artifact and hash:
- selected guidance keypoint artifact and hash:
- source-faithful joint contract and hash:
- C1 transform and hash:
- complete laptop mesh and hash:
- screen/lid and keyboard/base meshes and hashes:
- camera intrinsics/extrinsics and hashes:
- Gate-B semantic target and hash:

## Identity prerequisites

- H0 raw vertex-to-joint identity: [ ]
- H1 handedness/guidance identity: [ ]
- H2 projection identity: [ ]
- H3 shared-frame identity: [ ]
- H4 zero-update live-helper identity: [ ]
- physical upper-hand candidate source verified: [ ]

## First permitted optimization branch

Keep fixed:

- complete laptop geometry;
- lid/base relation and hinge state;
- camera;
- MANO shape and hand scale;
- non-active fingers initially.

Trainable, bounded:

- hand-root translation within the already registered Branch-E radius;
- hand-root rotation delta, initially no more than 10 degrees per axis;
- only Gate-B active-finger MANO joints, initially no more than 15-20 degrees per axis.

Loss order:

1. source-faithful 2D keypoint reprojection;
2. hand silhouette/image anchor;
3. strong initial-pose and joint-limit regularization;
4. weak screen/lid preference diagnostic;
5. contact and collision remain disabled until projection passes.

## Frozen acceptance gates

- normalized RMSE <= 0.50;
- normalized p95 <= 0.75;
- trust-region fraction < 0.98;
- proper/chirality-consistent solution only;
- pairwise shape threshold calibrated and frozen on `alapuse02v6n60`;
- silhouette non-regression;
- intended upper-hand and screen/lid preference;
- finite depth/projection;
- no severe penetration;
- object and camera hashes unchanged.

## Stop rule

One bounded run only. If it fails, do not enlarge the trust region or activate
contact/collision. Reclassify the failure before another branch.
