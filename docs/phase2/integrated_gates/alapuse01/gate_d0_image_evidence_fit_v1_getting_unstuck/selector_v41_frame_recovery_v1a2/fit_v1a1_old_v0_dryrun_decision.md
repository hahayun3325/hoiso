# alapuse01 — Gate D-0 fit v1a1 old v0 dry-run decision

## Decision

OLD_V0_DRYRUN_NOT_ENOUGH.

## Observation

The old v0 dry-run / active clean-parts frame can load the hand and laptop parts together, but the contact relation is still wrong.

The hand is not clearly touching the desired laptop lid/screen region. It touches or approaches the wrong part of the laptop.

## Interpretation

The v0 dry-run frame is useful as a loadability/debug scene, but it is not a reliable shared-frame contact seed.

## Next step

Recover the selector-v41 aligned frame, especially:

- `alapuse01_selector_v41_aligned_pred_vs_gt.glb`
- `selector_v41_alignment_transform_diagnostic_v2.json`
- the h2m transform from the selector-v41 full-pipeline run

Before using it for v1b, classify whether the alignment is:

1. non-GT usable, or
2. GT/oracle diagnostic only.
