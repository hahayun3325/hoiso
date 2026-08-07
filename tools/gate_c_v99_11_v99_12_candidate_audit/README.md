# v99.11–v99.12 Same-Run HaMeR Candidate Audit Toolkit

This toolkit is read-only. It inventories raw HaMeR batches, evaluates already-generated source-faithful zero-state candidate projections against an **independent upper-hand target**, generates indexed overlays, and writes a fail-closed route.

It does **not** reconstruct MANO candidates, change any pose, run an optimizer, move the object, enable contact/collision, or call a VLM.

## Critical target separation

- `historical_guidance_target`: use only to resolve which candidate was historically selected.
- `independent_upper_hand_target`: use for candidate ranking. This must not be derived solely from the historically selected candidate. Suitable evidence includes a source-valid upper-hand mask, independent detector/keypoints, ARCTIC annotation, or a manually reviewed target frozen before inspecting candidate scores.

## Typical sequence

1. Run `bootstrap_v99_11.sh`.
2. Run `inspect_hamer_batches.py` on the exact same-run HaMeR output directory.
3. Resolve raw-batch → selected-guidance/mesh lineage from source.
4. Use the existing source-bound HaMeR/MANO forward to export one zero-state `21x2` projection per candidate (and optional depth/mask arrays).
5. Fill `candidate_manifest.csv`.
6. Calibrate thresholds on the accepted `alapuse02v6n60` control and freeze `candidate_gate_policy.json` before viewing the v3 route.
7. Run `score_candidate_zero_states.py` and `write_candidate_route.py`.
8. Use `make_indexed_candidate_overlays.py` only after deterministic metrics are generated.
