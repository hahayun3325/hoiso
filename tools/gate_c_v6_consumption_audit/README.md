# v6 Accepted-Path Consumption Audit for `alapuse02v3n60` Gate C

This toolkit answers a narrower question than the earlier H0–H4 state-equivalence toolkit:

> Did the accepted `alapuse02v6n60` path actually consume the disputed internal 21-joint representation, or did it succeed through direct MANO mesh/fingertip vertices and saved 2D evidence that are shared by both representations?

That distinction is mandatory before using v6 to justify a canonical-joint helper or a mesh-helper route.

## Why this audit is needed

The project has already shown that:

- v3 transform and ordered 778-vertex serialization are sound;
- canonical wrapper joints and mesh-helper joints differ mainly in the internal skeletal joints;
- the five direct fingertip vertices agree to micrometer scale;
- accepted v6 contact and Gate-D reports explicitly use index/middle fingertip vertices and mesh-surface penetration metrics.

Therefore, a successful v6 result is not automatically a discriminating positive control. A control can decide the helper question only when the disputed joint producer lies on the accepted gradient, selector, or final-acceptance path.

## Safety contract

The toolkit is read-only. It does not:

- edit source;
- rewrite a target;
- move a hand or object;
- launch F3/F3.1/F3.3/F3.4/Gate D;
- authorize candidate scoring or MANO articulation.

## Installation

```bash
cd /home/fredcui/Projects/FollowMyHold
source /home/fredcui/anaconda3/etc/profile.d/conda.sh
conda activate foho

mkdir -p tools/gate_c_v6_consumption_audit
cp -a /PATH/TO/alapuse02v3n60_v6_consumption_path_audit_toolkit/. \
  tools/gate_c_v6_consumption_audit/

export REPO=/home/fredcui/Projects/FollowMyHold
export DATA=/home/fredcui/foho_phase0
export V6_CASE_ROOT="$DATA/phase2_gateA_part_recon/cases/alapuse02_v6_n60"
export V6_RUN_ROOT="$DATA/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse02v6n60_selector_v41_refined_pipeline"
export V3_CASE_ROOT="$DATA/vlm_failure_containment/alapuse02v3n60/inpainting_fallback/automatic_recovery_v2_part_graph"
export TOOL_ROOT="$REPO/tools/gate_c_v6_consumption_audit"
export AUDIT_ROOT="$V6_CASE_ROOT/gate_c0_v6_consumption_path_audit_v1"

bash "$TOOL_ROOT/bootstrap_v6_consumption_path_audit.sh"
```

## Step 1 — inspect the automatic inventory

```bash
sed -n '1,260p' "$AUDIT_ROOT/inventory/summary.md"
column -ts $'\t' "$AUDIT_ROOT/inventory/source_hits.tsv" | less -S
column -ts $'\t' "$AUDIT_ROOT/inventory/artifact_inventory.tsv" | less -S
cat "$AUDIT_ROOT/inventory/git_state.txt"
```

The automatic inventory is evidence discovery, not the decision.

## Step 2 — trace the accepted v6 causal path

Inspect the exact active implementation and logs:

```bash
cd "$REPO"

rg -n -C 10 \
  'mano_2d_kps|mano_3d_kps|pred_keypoints_3d|mano_vert_to_3dkps|J_regressor|TIP_IDS|target_tip_ids|320|443|FOHO_F3_|FOHO_F3_1|F3_3|F3_4|GATE_D|root_cleanup|selected_update|index.*target|middle.*target' \
  src scripts tools configs third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py \
  | tee "$AUDIT_ROOT/notes/focused_source_trace.txt"

find "$V6_CASE_ROOT" "$V6_RUN_ROOT" -type f \
  \( -iname '*F3*' -o -iname '*f3*' -o -iname '*gate*d*' \
     -o -iname '*kps*' -o -iname '*mano*' -o -iname '*contact*' \
     -o -iname '*target*' -o -iname '*decision*' -o -iname '*.env' \
     -o -iname '*.log' \) \
  -print | sort | tee "$AUDIT_ROOT/notes/focused_artifact_trace.txt"
```

For every accepted term, record whether it contributed:

```text
gradient
selector/checkpoint choice
final acceptance
or audit only
```

Then record the exact representation:

```text
canonical_21j
mesh_helper_21j
saved_2d_target
saved_3d_target
direct_fingertip_vertices
mesh_vertices
object_surface
camera_or_raster
other
unknown
```

## Step 3 — fill the source-confirmed manifest

```bash
$EDITOR "$AUDIT_ROOT/manifests/v6_loss_input_manifest.csv"
```

A row is `confirmed` only when `source_evidence` contains an exact file and line/range or a hashed runtime artifact proving the producer.

The key question is not whether a tensor existed. The key question is whether it influenced the accepted output.

## Step 4 — classify the positive control

```bash
python "$TOOL_ROOT/scripts/classify_v6_control.py" \
  --manifest "$AUDIT_ROOT/manifests/v6_loss_input_manifest.csv" \
  --out-dir "$AUDIT_ROOT/decision"

cat "$AUDIT_ROOT/decision/v6_consumption_decision.md"
```

Possible routes:

### `V6_DISCRIMINATES_CANONICAL_JOINT_CONSUMPTION`

Prepare a versioned canonical-joint adapter and run zero-update identity only. Do not move geometry yet.

### `V6_DISCRIMINATES_MESH_HELPER_JOINT_CONSUMPTION`

Keep the helper contract and proceed to the same-run physical-hand/candidate audit.

### `V6_MIXED_JOINT_CONSUMPTION_REQUIRES_TERM_SPLIT`

Separate the terms and run paired zero-update ablations. Do not globally replace the helper.

### `V6_FUNCTIONAL_CONTROL_ONLY_NONDISCRIMINATING`

Treat v6 as a functional contact/export control. Run source-faithful H0–H2 or a paired zero-update projection check; the success result alone cannot decide the helper.

### `HOLD_*`

Recover missing provenance or create one clean versioned control run. If neither is possible, close as a contained placement failure.

## Step 5 — write the next-route preregistration stub

```bash
python "$TOOL_ROOT/scripts/write_route_preregistration.py" \
  --decision "$AUDIT_ROOT/decision/v6_consumption_decision.json" \
  --out "$AUDIT_ROOT/preregistration/next_route_preregistration.md"

cat "$AUDIT_ROOT/preregistration/next_route_preregistration.md"
```

This remains non-authorizing.

## Required order after classification

```text
v6 consumption-path classification
→ source-faithful zero-update producer identity, if needed
→ v3 same-run physical-hand/candidate audit
→ one bounded placement family
→ Gate C2 consolidated verification
→ F3.4 / Gate D only after Gate C passes
```

## Frozen v3 placement criteria

Do not tune these after seeing a candidate:

```text
normalized RMSE <= 0.50
normalized p95 <= 0.75
trust-region fraction < 0.98
proper chirality only
exact target raster/crop contract
object geometry and camera hashes unchanged
silhouette non-regression
parameter bounds respected
```

## Scientific stopping rule

If the accepted v6 path cannot be reconstructed or does not exercise the disputed producer, do not infer helper correctness from success. Either establish source-faithful producer identity with a zero-update control or close v3 as a contained Gate-C placement failure.
