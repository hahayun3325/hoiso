# `alapuse02v3n60` Gate-C Hand-Hypothesis Audit Toolkit

This toolkit supports the professor-recommended next step after the rejected
translation-only and rigid/reflected diagnostics.

It is intentionally **non-destructive and non-authorizing**. It does not run
Hunyuan, HaMeR, MANO optimization, C2, F3.4, or Gate D.

## Scientific purpose

Answer one bounded question before opening another optimizer:

> Does a source-verified upper-hand/keypoint correspondence or alternate hand
> hypothesis exist in the frozen target raster?

The audit separates four failure classes:

1. wrong physical hand;
2. handedness/crop/raster mismatch;
3. joint-order mismatch;
4. correct hand identity but incompatible articulation.

A reflected fit is diagnostic evidence only. It never authorizes reflecting a
3D hand.

## Install in the repository

```bash
cd /home/fredcui/Projects/FollowMyHold
source /home/fredcui/anaconda3/etc/profile.d/conda.sh
conda activate foho

mkdir -p tools/gate_c_hand_hypothesis_audit
cp -a /PATH/TO/alapuse02v3n60_gate_c_hand_audit_toolkit/. \
  tools/gate_c_hand_hypothesis_audit/

bash tools/gate_c_hand_hypothesis_audit/bootstrap_gate_c_hand_audit.sh
```

The bootstrap writes:

```text
$CASE_ROOT/gate_c0_hand_identity_correspondence_audit_v1/
├── audit_context.json
├── inventory/
├── manifests/hand_candidates.csv
├── config/keypoint_mapping.json
├── config/raster_affine.json
├── config/thresholds.json
├── reports/
├── vlm/
└── decisions/
```

## Step 1 — inspect the candidate bank

```bash
export AUDIT_ROOT="$CASE_ROOT/gate_c0_hand_identity_correspondence_audit_v1"

sed -n '1,240p' "$AUDIT_ROOT/inventory/hand_candidate_files.txt"
sed -n '1,260p' "$AUDIT_ROOT/inventory/source_code_provenance_hits.txt"
```

Inspect array shapes without modifying them:

```bash
python tools/gate_c_hand_hypothesis_audit/scripts/inspect_artifacts.py \
  /ABS/PATH/candidate_keypoints.npy \
  /ABS/PATH/target_keypoints.npy \
  --out "$AUDIT_ROOT/inventory/selected_artifact_metadata.json"
```

## Step 2 — verify the coordinate contract

Before editing the manifest, trace and record:

- which detection is the physical upper hand;
- left/right handedness;
- whether the crop was mirrored;
- candidate joint order;
- target joint order;
- crop-to-full-image affine;
- whether candidate and target are in the exact same raster.

Then edit:

```bash
$EDITOR "$AUDIT_ROOT/manifests/hand_candidates.csv"
$EDITOR "$AUDIT_ROOT/config/keypoint_mapping.json"
$EDITOR "$AUDIT_ROOT/config/raster_affine.json"
```

Do not leave `unknown` fields and then interpret the resulting metric as a
correspondence pass.

## Step 3 — calibrate the structural threshold on `alapuse02v6n60`

Use the same script, mapping, raster convention, and known-positive upper-hand
candidate on the successful reference case. Record its
`pairwise_normalized_rmse`, then freeze the v3 threshold before viewing v3
candidate scores. A conservative development rule is:

```text
pairwise_normalized_rmse_max = 1.25 × positive-reference error
```

The existing normalized RMSE (`0.50`) and p95 (`0.75`) limits are inherited from
Branch E, but confirm that the audit uses the same target-bbox normalization
before changing `status` to `REGISTERED`.

```bash
$EDITOR "$AUDIT_ROOT/config/thresholds.json"
```

## Step 4 — run the deterministic audit

```bash
export TARGET_RGB=/ABS/PATH/exact_target_crop.png
export TARGET_KPS=/ABS/PATH/frozen_upper_hand_target_keypoints.npy
export TARGET_HAND_MASK=/ABS/PATH/target_upper_hand_mask.png  # optional

python tools/gate_c_hand_hypothesis_audit/scripts/audit_hand_candidates.py \
  --manifest "$AUDIT_ROOT/manifests/hand_candidates.csv" \
  --target-kps "$TARGET_KPS" \
  --thresholds "$AUDIT_ROOT/config/thresholds.json" \
  --image "$TARGET_RGB" \
  --target-mask "$TARGET_HAND_MASK" \
  --out-dir "$AUDIT_ROOT/reports"
```

A HOLD or FAIL is a successful audit outcome; the script returns without
launching another stage.

## Step 5 — optional spatially grounded VLM review

The VLM is a semantic critic, not a numerical transform solver. Build a contact
sheet:

```bash
python tools/gate_c_hand_hypothesis_audit/scripts/make_candidate_contact_sheet.py \
  --audit-summary "$AUDIT_ROOT/reports/hand_candidate_audit_summary.json" \
  --out "$AUDIT_ROOT/vlm/hand_candidate_contact_sheet.png"
```

Use the supplied `vlm_hand_choice_prompt.md`, save the untouched response as:

```text
$AUDIT_ROOT/vlm/raw_hand_choice_response.json
```

Validate it:

```bash
python tools/gate_c_hand_hypothesis_audit/scripts/validate_vlm_choice.py \
  --raw-response "$AUDIT_ROOT/vlm/raw_hand_choice_response.json" \
  --audit-summary "$AUDIT_ROOT/reports/hand_candidate_audit_summary.json" \
  --out "$AUDIT_ROOT/vlm/hand_choice_validation.json"
```

The VLM cannot authorize a reflected-only, invalid, or provenance-ambiguous
candidate.

## Step 6 — write the professor route

```bash
python tools/gate_c_hand_hypothesis_audit/scripts/write_gate_c_route.py \
  --audit-summary "$AUDIT_ROOT/reports/hand_candidate_audit_summary.json" \
  --vlm-validation "$AUDIT_ROOT/vlm/hand_choice_validation.json" \
  --out "$AUDIT_ROOT/decisions/professor_route.json"
```

Possible routes are:

```text
PREPARE_SELECTED_CANDIDATE_SHARED_FRAME_DRY_RUN
PREPARE_ONE_BOUNDED_SELECTED_JOINT_MANO_BRANCH
REPAIR_SOURCE_RASTER_OR_HANDEDNESS_METADATA_DO_NOT_REFLECT_3D_HAND
FREEZE_GATE_C_OR_FIND_SOURCE_VERIFIED_UPPER_HAND_CANDIDATE
```

## Step 7 — preregister, but do not launch, bounded articulation

Only use this when the selected candidate is source verified and the audit route
supports articulation review:

```bash
python tools/gate_c_hand_hypothesis_audit/scripts/preregister_bounded_articulation.py \
  --audit-summary "$AUDIT_ROOT/reports/hand_candidate_audit_summary.json" \
  --candidate-id REPLACE_WITH_SELECTED_ID \
  --branch-e-result "$BRANCH_E_RESULT" \
  --target-kps "$TARGET_KPS" \
  --mano-params /ABS/PATH/source_mano_parameters.npz \
  --hand-mask "$TARGET_HAND_MASK" \
  --object-assembly /ABS/PATH/fixed_complete_laptop.ply \
  --lid-mesh /ABS/PATH/screen_lid.ply \
  --base-mesh /ABS/PATH/keyboard_base.ply \
  --active-fingers thumb,index,middle \
  --out "$AUDIT_ROOT/decisions/bounded_articulation_preregistration.json"
```

The resulting record has `run_optimizer: false`. The actual optimizer should be
implemented only after confirming the source MANO-parameter format and the
existing repository rendering entry point.

## Gate reopening rule

```text
Gate C0 provenance/correspondence audit
  → PASS or source-verified articulation eligibility
Gate C1.5 bounded hypothesis/pose initialization
  → proper 2D fit + no trust saturation + pose bounds respected
Gate C2 part preference / projection / penetration verification
  → PASS
F3.4 and Gate D
  → only then reopen
```

Moving the laptop cannot repair a hand-only keypoint residual. ArtHOI-style
object-root ASR is a later, separate branch only when hand projection passes but
relative hand–laptop placement remains wrong. The complete lid/base assembly
must move as one rigid global similarity, with the internal hinge state frozen.
