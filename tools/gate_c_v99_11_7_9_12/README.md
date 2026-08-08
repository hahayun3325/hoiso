# v99.11.7.9.12 → v3 Hand Anchor Gate toolkit

This toolkit is fail-closed. It supports:

1. creating the indexed identity-review workspace for the 13 v6 quantitative survivors;
2. validating a completed identity review without forcing a semantic winner;
3. selecting a deterministic medoid anchor from multiple identity-valid survivors using frozen, re-anchored full-image keypoints;
4. writing a v3 one-execution authorization packet after the complete v6 selector is frozen.

It does **not** run HaMeR, run v3, move a hand/object, launch an optimizer, or enable contact/collision/flow.

## Required manifest for consensus selection

CSV columns:

```text
candidate_uid,keypoints_npy,neighbor_crop_consensus,full_image_keypoint_nrmse,normalized_metric_depth_residual
```

`keypoints_npy` must contain the source-frozen, re-anchored full-image 21×2 keypoints for that candidate.
