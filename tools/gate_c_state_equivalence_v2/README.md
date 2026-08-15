# Gate-C Hand-Keypoint State-Equivalence Toolkit v2

Case: `alapuse02v3n60`
Positive control: `alapuse02v6n60`

This toolkit audits the hand/keypoint observation contract before any new Gate-C placement or articulation optimization. It is deliberately fail-closed and non-destructive.

It never:

- rewrites the saved HaMeR target;
- guesses a joint permutation;
- reflects a hand;
- moves the hand or laptop;
- launches C2, F3.4, or Gate D.

## Scientific question

The active run has not yet shown that these states are equivalent under one source-faithful 21-joint contract:

```text
historical HaMeR batch
→ handedness-adjusted guidance
→ saved 2D projection
→ C1/shared-frame state
→ serialized zero-update MANO mesh
→ live-helper / mesh-derived joints
```

Current source is intended to use:

```text
16 MANO regressed joints
+ fingertips [744, 320, 443, 554, 671]
+ OpenPose-style map
  [0,13,14,15,16,1,2,3,17,4,5,6,18,10,11,12,19,7,8,9,20]
```

The audit therefore asks where the intended identity first breaks, not which arbitrary mapping gives the lowest error.

## What changed from v1

Version 2 fixes three unsafe weaknesses in the earlier audit helpers:

1. H3/H4 comparisons now apply frozen numerical tolerances and write an explicit `pass` field.
2. The route decision now verifies H2, H3, H4a, and H4b rather than accepting the mere presence of reports.
3. Historical and active contracts are interpreted separately; a historical target is never silently reinterpreted using active buffers.

H4 is split diagnostically:

```text
H4a: ordered 778-vertex source array → serialized/imported MANO mesh
H4b: exact zero-update mesh → source-faithful mesh-derived joints
```

## Installation

```bash
cd /home/fredcui/Projects/FollowMyHold
source /home/fredcui/anaconda3/etc/profile.d/conda.sh
conda activate foho

mkdir -p tools/gate_c_state_equivalence_v2
cp -a /PATH/TO/alapuse02v3n60_gate_c_state_equivalence_toolkit_v2/. \
  tools/gate_c_state_equivalence_v2/

export REPO=/home/fredcui/Projects/FollowMyHold
export DATA=/home/fredcui/foho_phase0
export CASE_ROOT="$DATA/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2"
export TOOL_ROOT="$REPO/tools/gate_c_state_equivalence_v2"
export AUDIT_ROOT="$CASE_ROOT/gate_c0_state_equivalence_v2"

bash "$TOOL_ROOT/bootstrap_gate_c_state_equivalence.sh"
```

Then fill:

```bash
$EDITOR "$AUDIT_ROOT/config/state_equivalence.env"
$EDITOR "$AUDIT_ROOT/manifests/state_ledger.csv"
source "$AUDIT_ROOT/config/state_equivalence.env"
```

## Gate order

Run the positive `alapuse02v6n60` control first using its own versioned audit root. Use it, plus same-process repeatability, to freeze the engineering tolerances. Do not tune thresholds after seeing whether v3 passes.

```text
positive-control calibration
→ H0/H1 historical-versus-active contract matrix
→ H2 projection identity
→ H3 C1/shared-frame identity
→ H4a mesh serialization identity
→ H4b live-helper identity
→ Gate C0-H physical-hand candidate audit
→ one preregistered bounded placement branch
```

## 1. Capture the active HaMeR contract

```bash
python "$TOOL_ROOT/scripts/capture_active_hamer_contract.py" \
  --repo "$REPO" \
  --hamer-root "$REPO/third_party/estimator/hamer" \
  --checkpoint '' \
  --out-dir "$AUDIT_ROOT/active_hamer_contract"
```

Expected files:

```text
active_hamer_contract.json
active_hamer_contract_buffers.npz
```

## 2. Hash the selected historical artifacts

After filling the environment template:

```bash
sha256sum \
  "$HAMER_BATCH_NPY" \
  "$GUIDANCE_NPY" \
  "$HISTORICAL_JREG" \
  "$TARGET_RGB" \
  "$C1_T" \
  "$C1_SOURCE_KPS" \
  "$ZERO_UPDATE_SOURCE_VERTICES" \
  "$ZERO_UPDATE_MANO" \
  "$ZERO_UPDATE_SOURCE_KPS" \
  | tee "$AUDIT_ROOT/inventory/selected_artifact_hashes.sha256"
```

Every file must belong to the same physical hand, same selected candidate, same run, and documented transform stage.

## 3. H0/H1 with the historical contract

```bash
python "$TOOL_ROOT/scripts/audit_saved_hamer_contract.py" \
  --batch-npy "$HAMER_BATCH_NPY" \
  --guidance-npy "$GUIDANCE_NPY" \
  --j-regressor "$HISTORICAL_JREG" \
  --candidate-index "$CANDIDATE_INDEX" \
  --thresholds "$AUDIT_ROOT/config/state_equivalence_thresholds.json" \
  --out-dir "$AUDIT_ROOT/reports/H0_H1_historical"
```

## 4. H0/H1 with the active contract

```bash
python "$TOOL_ROOT/scripts/audit_saved_hamer_contract.py" \
  --batch-npy "$HAMER_BATCH_NPY" \
  --guidance-npy "$GUIDANCE_NPY" \
  --contract-npz "$AUDIT_ROOT/active_hamer_contract/active_hamer_contract_buffers.npz" \
  --candidate-index "$CANDIDATE_INDEX" \
  --thresholds "$AUDIT_ROOT/config/state_equivalence_thresholds.json" \
  --out-dir "$AUDIT_ROOT/reports/H0_H1_active"
```

## 5. Compare historical and active buffers

```bash
python "$TOOL_ROOT/scripts/compare_contract_buffers.py" \
  --historical-j-regressor "$HISTORICAL_JREG" \
  --active-contract-npz "$AUDIT_ROOT/active_hamer_contract/active_hamer_contract_buffers.npz" \
  --out "$AUDIT_ROOT/reports/contract_buffer_comparison.json" || true
```

A `HOLD` here is evidence of version drift, not an instruction to overwrite the historical contract.

## 6. Interpret the contract matrix

```bash
python "$TOOL_ROOT/scripts/summarize_contract_matrix.py" \
  --historical "$AUDIT_ROOT/reports/H0_H1_historical/report.json" \
  --active "$AUDIT_ROOT/reports/H0_H1_active/report.json" \
  --buffer-comparison "$AUDIT_ROOT/reports/contract_buffer_comparison.json" \
  --out-dir "$AUDIT_ROOT/reports/contract_matrix"
```

Interpretation:

```text
historical passes, active fails:
  preserve historical branch; recover historical dependencies or rerun active as a new branch.

active passes, historical fails:
  quarantine historical J-regressor as stale/unrelated; regenerate all hand-derived artifacts in a new active branch.

both pass, buffers equivalent:
  continue using the historical branch; active is consistent.

both pass, buffers differ:
  use historical for historical-run lineage; do not mix versions.

both fail:
  stop before H2; recover candidate/run/checkpoint/MANO/handedness provenance.
```

## 7. H2 projection identity

Use the exact raster that generated `mano_2d_kps`; do not use a panel image or later resize.

```bash
python "$TOOL_ROOT/scripts/reproject_saved_guidance.py" \
  --guidance-npy "$GUIDANCE_NPY" \
  --image "$TARGET_RGB" \
  --active-contract-json "$AUDIT_ROOT/active_hamer_contract/active_hamer_contract.json" \
  --thresholds "$AUDIT_ROOT/config/state_equivalence_thresholds.json" \
  --out-dir "$AUDIT_ROOT/reports/H2_projection_identity"
```

If the contract matrix selected the historical contract and its focal/image configuration differs from the active model, pass the historical values explicitly through `--base-focal` and `--model-image-size`; record them in the state ledger.

## 8. H3 C1/shared-frame identity

Choose the handed 3D target produced by the selected contract:

```bash
# Example for the historical branch:
export SELECTED_H01="$AUDIT_ROOT/reports/H0_H1_historical"
```

Apply the exact frozen C1 transform without fitting:

```bash
python "$TOOL_ROOT/scripts/apply_frozen_transform.py" \
  --points "$SELECTED_H01/handed_target_3d.npy" \
  --transform "$C1_T" \
  --out-dir "$AUDIT_ROOT/reports/H3_source_through_C1"
```

Compare against an independently produced source-keypoint array in the same C1 frame:

```bash
python "$TOOL_ROOT/scripts/compare_keypoint_arrays.py" \
  --a "$AUDIT_ROOT/reports/H3_source_through_C1/transformed_points.npy" \
  --b "$C1_SOURCE_KPS" \
  --stage H3_shared_frame_identity \
  --units m \
  --thresholds "$AUDIT_ROOT/config/state_equivalence_thresholds.json" \
  --out "$AUDIT_ROOT/reports/H3_shared_frame_identity.json"
```

No new similarity fit is permitted in H3.

## 9. H4a ordered mesh serialization identity

The safest practice is to save the exact ordered zero-update 778x3 vertex array as `.npy` before PLY/OBJ export.

```bash
python "$TOOL_ROOT/scripts/check_mano_mesh_roundtrip.py" \
  --source-vertices "$ZERO_UPDATE_SOURCE_VERTICES" \
  --mesh "$ZERO_UPDATE_MANO" \
  --thresholds "$AUDIT_ROOT/config/state_equivalence_thresholds.json" \
  --out "$AUDIT_ROOT/reports/H4a_mesh_serialization_identity.json"
```

H4a catches remeshing, decimation, vertex reordering, scale changes, and export/import drift.

## 10. H4b exact zero-update live-helper identity

Derive source-faithful joints from the exact serialized mesh using the selected contract. Example for the historical contract:

```bash
python "$TOOL_ROOT/scripts/joints_from_mano_mesh.py" \
  --mesh "$ZERO_UPDATE_MANO" \
  --j-regressor "$HISTORICAL_JREG" \
  --out-dir "$AUDIT_ROOT/reports/H4b_mesh_derived"
```

Or, only when the contract matrix selected active:

```bash
python "$TOOL_ROOT/scripts/joints_from_mano_mesh.py" \
  --mesh "$ZERO_UPDATE_MANO" \
  --contract-npz "$AUDIT_ROOT/active_hamer_contract/active_hamer_contract_buffers.npz" \
  --out-dir "$AUDIT_ROOT/reports/H4b_mesh_derived"
```

Then compare direct identity in the same frame:

```bash
python "$TOOL_ROOT/scripts/compare_keypoint_arrays.py" \
  --a "$ZERO_UPDATE_SOURCE_KPS" \
  --b "$AUDIT_ROOT/reports/H4b_mesh_derived/mesh_derived_joints.npy" \
  --stage H4_live_helper_identity \
  --units m \
  --thresholds "$AUDIT_ROOT/config/state_equivalence_thresholds.json" \
  --out "$AUDIT_ROOT/reports/H4_live_helper_identity.json"
```

## 11. Route the result

```bash
python "$TOOL_ROOT/scripts/decide_state_equivalence_route.py" \
  --contract-matrix "$AUDIT_ROOT/reports/contract_matrix/contract_matrix.json" \
  --h2 "$AUDIT_ROOT/reports/H2_projection_identity/report.json" \
  --h3 "$AUDIT_ROOT/reports/H3_shared_frame_identity.json" \
  --h4a "$AUDIT_ROOT/reports/H4a_mesh_serialization_identity.json" \
  --h4 "$AUDIT_ROOT/reports/H4_live_helper_identity.json" \
  --out-dir "$AUDIT_ROOT/decision"

cat "$AUDIT_ROOT/decision/decision.md"
```

The only ready route is:

```text
READY_FOR_SOURCE_VERIFIED_GATE_C0_H_CANDIDATE_AUDIT
```

That route authorizes only deterministic same-run candidate scoring. It does not authorize placement, articulation, C2, F3.4, or Gate D.

## 12. If the historical run cannot be reproduced

Do not mutate historical files. Run HaMeR again in an empty, versioned workspace so a stale `J_regressor_hamer.pt` cannot be inherited:

```bash
export EXACT_HAMER_INPUT_DIR=/ABS/PATH/to/exact_hand_crop_folder
export EXACT_FULL_IMAGE_DIR=/ABS/PATH/to/exact_full_image_folder
export FRESH_WS="$AUDIT_ROOT/fresh_active_hamer_workspace"
export FRESH_OUT="$AUDIT_ROOT/fresh_active_hamer_output"

mkdir -p "$FRESH_WS" "$FRESH_OUT"

(
  cd "$FRESH_WS" || exit 1
  rm -f ./J_regressor_hamer.pt

  PYTHONPATH="$REPO/src:$REPO/third_party/estimator/hamer:${PYTHONPATH:-}" \
  python -m foho.hand.hamer \
    --hamer_demo_dir "$REPO/third_party/estimator/hamer" \
    --img_folder "$EXACT_HAMER_INPUT_DIR" \
    --out_folder "$FRESH_OUT" \
    --full_img_dir "$EXACT_FULL_IMAGE_DIR" \
    --save_mesh \
    --batch_size 1 \
    --rescale_factor 2.0 \
    --body_detector vitdet \
    --file_type '*.png' '*.jpg'
)
```

Treat this as a new branch. Regenerate guidance, mesh, projection, and C1 outputs together. Do not pair a fresh active mesh with an old historical target.

## 13. After H0-H4 pass

Proceed in this order:

```text
Gate C0-H: same-run physical upper-hand identity / handedness audit
→ deterministic projection and silhouette scoring
→ optional indexed VLM review as a secondary critic
→ one preregistered bounded root + active-finger trial
→ Gate C2 projection / lid preference / distance / penetration review
→ F3.4 and Gate D only after C2 passes
```

For the first post-lineage branch:

```text
trainable:
  root translation
  root axis-angle correction
  Gate-B active-finger joints

frozen:
  MANO shape and scale
  non-active fingers initially
  camera
  complete laptop geometry
  hinge state
```

Use the supplied preregistration template. Contact attraction and collision remain off until projection passes.

## 14. Explicit hold conditions

Until H0-H4 pass:

```text
target rewrite:       false
guessed mapping:      false
reflection:           false
candidate scoring:    false
mesh movement:        false
MANO articulation:    false
contact/collision:    false
C2:                   false
F3.4:                 false
Gate D:               false
```
