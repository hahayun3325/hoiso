# Gate-C Keypoint-Lineage Audit Toolkit

Case: `alapuse02v3n60`

Purpose: recover and verify the exact relationship between HaMeR's saved
`pred_keypoints_3d`, the saved HaMeR vertices, the handedness-adjusted guidance
keypoints, and the mesh-derived keypoints used by the live FollowMyHold helper.

This toolkit is deliberately **non-authorizing**. It never moves a mesh, launches
C2, runs F3.4, or opens Gate D. Its only job is to answer the keypoint contract.

## Why this audit is now narrower than the earlier inquiry

Current upstream source shows the intended construction on both sides:

- HaMeR obtains `pred_keypoints_3d` from `mano_output.joints`.
- HaMeR's MANO wrapper builds those joints from the 16 MANO regressed joints,
  appends five fingertip vertices, and applies one OpenPose-style 21-joint map.
- FollowMyHold's `mano_vert_to_3dkps` helper uses the same five fingertip vertex
  IDs and the same 21-joint map.

Therefore, the immediate question is not "which arbitrary permutation looks
best?" It is:

> Does the active local checkout, checkpoint, MANO asset, selected hand,
> chirality stage, and transformed mesh reproduce that intended identity?

The audit ladder localizes the first stage where identity breaks:

```text
H0  raw HaMeR vertices -> raw HaMeR pred_keypoints_3d
H1  handedness-adjusted HaMeR joints -> saved guidance 3D joints
H2  saved guidance 3D joints -> saved guidance 2D projection
H3  source-faithful joints after C1/shared-frame transform
H4  live-helper joints from the exact zero-update aligned mesh
```

## Installation

Copy this folder into the FollowMyHold checkout:

```bash
cd /home/fredcui/Projects/FollowMyHold
mkdir -p tools/gate_c_keypoint_lineage
cp -a /PATH/TO/alapuse02v3n60_gate_c_keypoint_lineage_toolkit/. \
  tools/gate_c_keypoint_lineage/
```

Then bootstrap the read-only audit:

```bash
cd /home/fredcui/Projects/FollowMyHold
source /home/fredcui/anaconda3/etc/profile.d/conda.sh
conda activate foho

export REPO=/home/fredcui/Projects/FollowMyHold
export DATA=/home/fredcui/foho_phase0
export CASE_ROOT="$DATA/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2"
export AUDIT_ROOT="$CASE_ROOT/gate_c_keypoint_lineage_v1"

bash tools/gate_c_keypoint_lineage/bootstrap_gate_c_lineage.sh
```

The bootstrap records:

- repository commit and working-tree diff;
- hashes of all relevant source files;
- exact local definitions of `pred_keypoints_3d`, fingertip indices, joint map,
  handedness conversion, and `mano_vert_to_3dkps`;
- candidate `.npy`, mesh, keypoint, transform, and camera artifacts;
- a manifest that must be filled before any metric is trusted.

## Stage H0/H1: audit the saved HaMeR output

First locate the files:

```bash
sed -n '1,260p' "$AUDIT_ROOT/inventory/likely_lineage_artifacts.txt"
find "$REPO" "$CASE_ROOT" -type f -name 'J_regressor_hamer.pt' -print
```

Then fill these values from the inventory:

```bash
export HAMER_BATCH_NPY=/ABS/PATH/to/the/full_saved_hamer_batch.npy
export GUIDANCE_NPY=/ABS/PATH/to/the/selected_kps_for_guidance.npy
export JREG=/ABS/PATH/to/J_regressor_hamer.pt
export CANDIDATE_INDEX=0
```

Run the saved-output identity audit:

```bash
python tools/gate_c_keypoint_lineage/scripts/audit_saved_hamer_contract.py \
  --batch-npy "$HAMER_BATCH_NPY" \
  --guidance-npy "$GUIDANCE_NPY" \
  --j-regressor "$JREG" \
  --candidate-index "$CANDIDATE_INDEX" \
  --thresholds tools/gate_c_keypoint_lineage/config/lineage_thresholds.json \
  --out-dir "$AUDIT_ROOT/reports/H0_H1_saved_output"
```

Interpretation:

```text
H0 FAIL:
  active/saved J_regressor, fingertip IDs, joint order, checkpoint, MANO asset,
  vertex topology, or candidate identity does not match the saved target.

H0 PASS, H1 FAIL:
  raw semantics agree; the failure begins at handedness, selected-candidate,
  or guidance-file construction.

H0 PASS, H1 PASS:
  the source joint contract is established through the guidance 3D file.
  Continue to H2; do not launch placement yet.
```

## Capture the active model contract

This reads the model buffers from the active checkout and checkpoint without
running the full reconstruction pipeline:

```bash
python tools/gate_c_keypoint_lineage/scripts/capture_active_hamer_contract.py \
  --repo "$REPO" \
  --hamer-root "$REPO/third_party/estimator/hamer" \
  --checkpoint '' \
  --out-dir "$AUDIT_ROOT/active_hamer_contract"
```

It records the active:

- `J_regressor`;
- `extra_joints_idxs`;
- `joint_map`;
- optional extra regressor;
- checkpoint/config/source hashes.

Compare that active contract with the J-regressor and source used by the
historical run before declaring H0 a semantic failure.

## H2: reproduce the saved full-image projection

Use the same target RGB that produced the HaMeR guidance file:

```bash
export TARGET_RGB=/ABS/PATH/to/the/exact_target_crop_or_full_raster.png

python tools/gate_c_keypoint_lineage/scripts/reproject_saved_guidance.py \
  --guidance-npy "$GUIDANCE_NPY" \
  --image "$TARGET_RGB" \
  --active-contract-json "$AUDIT_ROOT/active_hamer_contract/active_hamer_contract.json" \
  --thresholds tools/gate_c_keypoint_lineage/config/lineage_thresholds.json \
  --out-dir "$AUDIT_ROOT/reports/H2_projection_identity"
```

This reproduces the official FollowMyHold calculation using the saved
handedness-adjusted 3D joints, full-image camera translation, scaled focal
length, and image center.

## H3/H4 comparisons

Use `compare_keypoint_arrays.py` for any two frozen 21x2 or 21x3 arrays:

```bash
python tools/gate_c_keypoint_lineage/scripts/compare_keypoint_arrays.py \
  --a /ABS/PATH/source_array.npy \
  --b /ABS/PATH/reproduced_array.npy \
  --stage H3_shared_frame_identity \
  --units m \
  --out "$AUDIT_ROOT/reports/H3_shared_frame_identity.json"
```

The script reports direct, x-reflected, centered-shape, and pairwise-distance
metrics. Reflection is diagnostic only and never authorizes a reflected hand.

For H3 and H4, compare arrays generated from the **same selected candidate**
and **same zero-update mesh**. Do not compare a pre-flip raw target to a
post-flip mesh-derived helper output.

Generate H3 with the exact frozen C1 transform, then compare it against the
independently produced C1 keypoints:

```bash
python tools/gate_c_keypoint_lineage/scripts/apply_frozen_transform.py \
  --points "$AUDIT_ROOT/reports/H0_H1_saved_output/handed_target_3d.npy" \
  --transform /ABS/PATH/to/the/exact_C1_4x4_transform.npy \
  --out-dir "$AUDIT_ROOT/reports/H3_source_through_C1"

python tools/gate_c_keypoint_lineage/scripts/compare_keypoint_arrays.py \
  --a "$AUDIT_ROOT/reports/H3_source_through_C1/transformed_points.npy" \
  --b /ABS/PATH/to/independent_C1_source_keypoints.npy \
  --stage H3_shared_frame_identity \
  --units m \
  --out "$AUDIT_ROOT/reports/H3_shared_frame_identity.json"
```

Generate H4 directly from the exact zero-update 778-vertex MANO mesh:

```bash
python tools/gate_c_keypoint_lineage/scripts/joints_from_mano_mesh.py \
  --mesh /ABS/PATH/to/exact_zero_update_aligned_mano_mesh.ply \
  --contract-npz "$AUDIT_ROOT/active_hamer_contract/active_hamer_contract_buffers.npz" \
  --out-dir "$AUDIT_ROOT/reports/H4_mesh_derived"

python tools/gate_c_keypoint_lineage/scripts/compare_keypoint_arrays.py \
  --a /ABS/PATH/to/source_keypoints_in_the_same_zero_update_frame.npy \
  --b "$AUDIT_ROOT/reports/H4_mesh_derived/mesh_derived_joints.npy" \
  --stage H4_live_helper_identity \
  --units m \
  --out "$AUDIT_ROOT/reports/H4_live_helper_identity.json"
```

## Route decision

After H0-H4 reports exist:

```bash
python tools/gate_c_keypoint_lineage/scripts/decide_lineage_route.py \
  --h0 "$AUDIT_ROOT/reports/H0_H1_saved_output/report.json" \
  --h2 "$AUDIT_ROOT/reports/H2_projection_identity.json" \
  --h3 "$AUDIT_ROOT/reports/H3_shared_frame_identity.json" \
  --h4 "$AUDIT_ROOT/reports/H4_live_helper_identity.json" \
  --out-dir "$AUDIT_ROOT/decision"
```

Possible decisions:

```text
ROUTE_J_ACTIVE_SOURCE_OR_STATE_MISMATCH
ROUTE_J_CHIRALITY_OR_GUIDANCE_STAGE_MISMATCH
HOLD_BEFORE_H2_PROJECTION_IDENTITY
HOLD_BEFORE_H3_SHARED_FRAME_IDENTITY
HOLD_BEFORE_H4_LIVE_HELPER_IDENTITY
READY_FOR_SOURCE_VERIFIED_CANDIDATE_AUDIT
ROUTE_U_CONTAINED_LINEAGE_FAILURE
```

Route M is intentionally not inferred numerically. It requires a separate
human-authored `source_proven_mapping.json` that cites exact local source lines.

## After the identity ladder passes

Only after H0-H4 pass:

1. evaluate all saved same-run HaMeR candidates;
2. select the physical upper hand using source metadata and deterministic
   projection gates;
3. preregister one bounded root/active-finger refinement;
4. keep the laptop fixed for that first hand-side experiment;
5. reopen C2 only after projection, lid preference, penetration, and trust-region
   gates pass;
6. keep F3.4 and Gate D closed until C2 passes.

## Important source-stage distinction

The current FollowMyHold source saves the full HaMeR output before applying the
external handedness flip used for the guidance keypoints and mesh. Thus these
are not interchangeable:

```text
full batch pred_keypoints_3d:  raw model/MANO convention
kps_for_guidance mano_3d_kps: handedness-adjusted convention
exported selected hand mesh:   handedness-adjusted convention
```

This distinction must be written into the artifact manifest.
