# v99.11.7.9.21.7.12 Metric-Contract Diagnostic Toolkit

Read-only utilities for the `alapuse02v3n60` Hand Anchor Gate diagnosis.

The toolkit does **not** run HaMeR, modify thresholds, select a crop, move the hand, or launch any optimizer.

## Files

- `bootstrap_metric_contract_audit.sh`: creates a fail-closed audit workspace.
- `scripts/compare_metric_distributions.py`: compares frozen v6 and v3 candidate metric distributions.
- `scripts/audit_candidate_bindings.py`: verifies that per-candidate arrays and mesh inputs are actually distinct and bound to the expected candidate UIDs.
- `scripts/make_512_joint_overlay.py`: draws target and projected 21-joint arrays on the exact full-image raster.
- `config/frame_contract_review.template.json`: template for proving the coordinate semantics of the depth metric.
- `config/candidate_binding_manifest.template.csv`: template for candidate-specific paths.

## Required order

1. Freeze current v6/v3 result hashes.
2. Audit candidate bindings.
3. Review source and complete the frame-contract template.
4. Compare v6/v3 metric distributions.
5. Generate representative full-raster joint overlays.
6. Decide whether to repair a metric, restage the gate, or close the v3 family.
