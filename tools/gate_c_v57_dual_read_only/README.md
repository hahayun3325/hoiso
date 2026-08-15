# v57 Dual Read-Only Gate-C Toolkit

This toolkit implements the professor-recommended next step after the reported v56 shared-adapter closure:

1. a provenance-first audit of the pre-/post-Gate-A object root; and
2. routing that combines that audit with the existing read-only articulation-adequacy decision.

It never launches nonzero placement, contact, collision, flow guidance, C2, F3.4, or Gate D.

## Important correction to the draft inquiry script

A GLB `trimesh.Scene` must be flattened with its node transforms applied. Concatenating `scene.geometry.values()` alone can discard scene-graph transforms and produce a false root-scale/pose diagnosis. The supplied audit uses `Scene.dump(concatenate=True)` and reports scene nodes.

A sampled similarity fit is diagnostic only. If Gate A is claimed to be a fixed partition of one mesh, provide an explicit vertex map or a source-proven same-index contract. Without that lineage, a near-identity geometric fit is not enough to authorize a route.

## Install

```bash
cd /home/fredcui/Projects/FollowMyHold
source /home/fredcui/anaconda3/etc/profile.d/conda.sh
conda activate foho

mkdir -p tools/gate_c_v57_dual_read_only
cp -a /PATH/TO/alapuse02v3n60_v57_dual_read_only_gate_c_toolkit/. \
  tools/gate_c_v57_dual_read_only/

export REPO=/home/fredcui/Projects/FollowMyHold
export DATA=/home/fredcui/foho_phase0
export CASE_ROOT="$DATA/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2"
export TOOL_ROOT="$REPO/tools/gate_c_v57_dual_read_only"
export AUDIT_ROOT="$CASE_ROOT/gate_c1_5_v57_dual_read_only_alignment_audit"

bash "$TOOL_ROOT/bootstrap_v57_dual_read_only_gate_c.sh"
```

## Validate the reported v56 route

```bash
export METHOD_ROOT="$CASE_ROOT/gate_c1_physical_hand_placement_method_v27"
export V56_ROUTE="$METHOD_ROOT/v3_projection_reference_closure_v56/reports/projection_reference_closure_route_v56.json"

python "$TOOL_ROOT/scripts/validate_v56_route.py" \
  --route "$V56_ROUTE" \
  --out "$AUDIT_ROOT/inventory/v56_route_validation.json"
```

## Bind exact object artifacts

Review the inventory and fill the lineage manifest. Do not guess paths.

```bash
less "$AUDIT_ROOT/inventory/object_and_lineage_artifacts.txt"
$EDITOR "$AUDIT_ROOT/config/object_lineage_manifest.csv"

export PRE_PART_OBJECT=/ABS/PATH/pre_gate_a_whole_object.ply
export POST_PART_OBJECT=/ABS/PATH/post_gate_a_assembled_object.glb
export VERTEX_MAP=/ABS/PATH/source_to_assembled_vertex_map.npy   # optional but strongly preferred
```

Inspect each scene before fitting:

```bash
python "$TOOL_ROOT/scripts/inspect_mesh_scene.py" \
  --input "$PRE_PART_OBJECT" \
  --out "$AUDIT_ROOT/root_audit/pre_scene.json"
python "$TOOL_ROOT/scripts/inspect_mesh_scene.py" \
  --input "$POST_PART_OBJECT" \
  --out "$AUDIT_ROOT/root_audit/post_scene.json"
```

## Run root audit

For a true fixed-mesh partition with a known vertex map:

```bash
python "$TOOL_ROOT/scripts/audit_part_aware_root_contract.py" \
  --source "$PRE_PART_OBJECT" \
  --target "$POST_PART_OBJECT" \
  --out-dir "$AUDIT_ROOT/root_audit" \
  --thresholds "$AUDIT_ROOT/config/root_audit_thresholds.json" \
  --lineage-mode fixed_partition \
  --correspondence "$VERTEX_MAP"
```

If the accepted post-Gate-A object is known to be a different Hunyuan candidate:

```bash
python "$TOOL_ROOT/scripts/audit_part_aware_root_contract.py" \
  --source "$PRE_PART_OBJECT" \
  --target "$POST_PART_OBJECT" \
  --out-dir "$AUDIT_ROOT/root_audit" \
  --thresholds "$AUDIT_ROOT/config/root_audit_thresholds.json" \
  --lineage-mode candidate_substitution
```

The second route is diagnostic only. Do not use the fitted similarity as the metric object pose. A substituted normalized object must be aligned to the accepted image/depth/mask evidence in its own right.

## Run the existing articulation probe in parallel

Use the existing `alapuse02v3n60_gate_c_articulation_adequacy_toolkit_v1` after refactoring the v56 zero forward into one shared source-bound forward used by both:

```text
source_bound_hand_forward_v57.py
  ├── v56 zero adapter: deltas = {}
  └── read-only probe adapter: whitelisted ephemeral deltas
```

The read-only adapter must clone tensors, return only projected keypoints, rerun zero after perturbations, and write no nonzero state or mesh.

After the existing toolkit writes:

```text
$ART_AUDIT_ROOT/decision/decision.json
```

combine the routes:

```bash
python "$TOOL_ROOT/scripts/decide_dual_read_only_route.py" \
  --root-report "$AUDIT_ROOT/root_audit/root_contract_report.json" \
  --articulation-decision "$ART_AUDIT_ROOT/decision/decision.json" \
  --out-dir "$AUDIT_ROOT/decision"

cat "$AUDIT_ROOT/decision/decision.md"
```

No route produced here directly launches an optimizer.
