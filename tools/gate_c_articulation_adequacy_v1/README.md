# Gate-C Read-Only Articulation-Adequacy Toolkit v1

Case: `alapuse02v3n60`
Positive control: `alapuse02v6n60`

This toolkit answers one bounded question:

> Around the validated zero-update MANO state, can source-bound local articulation—or translation plus selected articulation—explain the frozen target-raster residual within preregistered bounds?

It is deliberately read-only. The finite-difference evaluations are ephemeral and return only 2D keypoints. The toolkit never exports a perturbed mesh, updates a checkpoint, moves the laptop, launches contact/collision, or authorizes Gate D.

## Scientific blocks

The default nested comparison is:

```text
active_articulation
translation_only
translation_plus_active
all_articulation_upper_bound
diagnostic_full_upper_bound
```

Only the first and third blocks can support a later trial. Full-hand or root-rotation upper bounds are diagnostic only.

## Professor-recommended policy

- Use the exact source-bound MANO wrapper, handedness convention, C1 transform, camera, raster, and keypoint order.
- Keep `global_orient`/root rotation out of the first authorizing block; the rigid-root family was already rejected.
- Use Gate-B active fingers first—normally index and middle, plus thumb only when the image/contact record supports it.
- Use all MANO articulation only as an over-parameterized sensitivity ceiling.
- Run keypoint Jacobians first. Silhouette is a later anti-regression check, not part of the first rank decision.
- Calibrate finite-difference stability and thresholds on the v6 control and synthetic known perturbations before looking at the v3 route.

## Install

```bash
cd /home/fredcui/Projects/FollowMyHold
source /home/fredcui/anaconda3/etc/profile.d/conda.sh
conda activate foho

mkdir -p tools/gate_c_articulation_adequacy_v1
cp -a /PATH/TO/alapuse02v3n60_gate_c_articulation_adequacy_toolkit_v1/. \
  tools/gate_c_articulation_adequacy_v1/

export REPO=/home/fredcui/Projects/FollowMyHold
export DATA=/home/fredcui/foho_phase0
export CASE_ROOT="$DATA/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2"
export TOOL_ROOT="$REPO/tools/gate_c_articulation_adequacy_v1"
export AUDIT_ROOT="$CASE_ROOT/gate_c1_5_read_only_articulation_adequacy_v1"

bash "$TOOL_ROOT/bootstrap_gate_c_articulation_adequacy.sh"
```

Then edit and source:

```bash
$EDITOR "$AUDIT_ROOT/config/articulation_adequacy.env"
source "$AUDIT_ROOT/config/articulation_adequacy.env"

$EDITOR "$PARAMETER_MANIFEST"
$EDITOR "$SOURCE_ADAPTER"
$EDITOR "$PROBE_CONFIG"
```

## 0. Positive-control and synthetic calibration

The accepted v6 path is a translation-only functional control, so it is not by itself a positive articulation example. Before looking at v3, use the exact v6 source adapter to create a small **synthetic** target from a known 5-degree active-joint perturbation and a separate known 1-mm translation. The probe should recover at least 95% residual energy for the matching block and should select the injected block. Freeze thresholds after this calibration.

Example:

```bash
cat > "$V6_AUDIT_ROOT/config/synthetic_active_delta.json" <<'EOF'
{
  "EXACT_ACTIVE_PARAMETER_NAME": 0.08726646259971647
}
EOF

python "$TOOL_ROOT/scripts/make_source_bound_synthetic_target.py" \
  --config "$V6_PROBE_CONFIG" \
  --deltas-json "$V6_AUDIT_ROOT/config/synthetic_active_delta.json" \
  --out "$V6_AUDIT_ROOT/calibration/synthetic_active_target.npy"
```

Create a versioned calibration config that points `target_keypoints` to that file, then run the same preflight/FD/analysis/decision sequence. This validates the derivative implementation; it is not evidence that the real v3 residual is articulatable.

## 1. Preflight exact zero identity

```bash
python "$TOOL_ROOT/scripts/preflight_articulation_probe.py" \
  --config "$PROBE_CONFIG" \
  --out-dir "$AUDIT_ROOT/preflight"

cat "$AUDIT_ROOT/preflight/preflight.json"
```

Required:

```text
status = PASS
zero identity max <= 0.05 px
zero identity RMSE <= 0.01 px
normalization_scale_px = exact registered Branch-E denominator
```

## 2. Collect finite differences

```bash
python "$TOOL_ROOT/scripts/collect_fd_jacobian.py" \
  --config "$PROBE_CONFIG" \
  --preflight "$AUDIT_ROOT/preflight/preflight.json" \
  --out-dir "$AUDIT_ROOT/fd"

cat "$AUDIT_ROOT/fd/fd_collection.json"
column -s, -t < "$AUDIT_ROOT/fd/fd_stability.csv" | less -S
```

The default checks central differences at 0.25°, 0.5°, and 1.0° when the manifest step is 0.5°. Translation uses the source-declared step, normally 0.5–1 mm. When translation is enabled, set `BRANCH_E_TRANSLATION_RADIUS_M` to the exact registered L2 trust radius; the analyzer enforces the spherical trust region rather than an unsafe per-axis box alone. The adapter is called again at zero after all perturbations to detect accidental state mutation.

## 3. Analyze rank and bounded residual span

```bash
python "$TOOL_ROOT/scripts/analyze_articulation_adequacy.py" \
  --config "$PROBE_CONFIG" \
  --preflight-dir "$AUDIT_ROOT/preflight" \
  --fd-dir "$AUDIT_ROOT/fd" \
  --out-dir "$AUDIT_ROOT/analysis"

column -s, -t < "$AUDIT_ROOT/analysis/block_summary.csv" | less -S
```

The analyzer uses a bound-normalized Jacobian and reports:

- finite-difference-stable parameter count;
- effective SVD rank and condition;
- unbounded span coverage;
- bounded least-squares coverage with each parameter constrained to its preregistered limit;
- predicted normalized RMSE and p95;
- bound saturation;
- per-parameter linearized deltas.

Default adequacy screen:

```text
bounded weighted residual-energy coverage >= 0.80
bounded residual-norm ratio <= 0.45
RMSE reduction >= 50%
predicted normalized RMSE <= 0.65
predicted normalized p95 <= 1.00
max parameter bound fraction <= 0.90
saturated parameter fraction <= 0.10
registered group L2 trust fraction <= 0.90
effective condition <= 1e4
```

These are **trial-screening** thresholds, not final Gate-C acceptance. A later nonzero trial still must satisfy the registered final limits `nRMSE <= 0.50`, `np95 <= 0.75`, and trust fraction `< 0.98`, plus silhouette and identity anti-regression.

## 4. Route the result

```bash
python "$TOOL_ROOT/scripts/decide_articulation_route.py" \
  --preflight "$AUDIT_ROOT/preflight/preflight.json" \
  --fd "$AUDIT_ROOT/fd/fd_collection.json" \
  --analysis "$AUDIT_ROOT/analysis/analysis_summary.json" \
  --out-dir "$AUDIT_ROOT/decision"

cat "$AUDIT_ROOT/decision/decision.md"
```

Possible routes:

```text
ROUTE_A_PREREGISTER_BOUNDED_ACTIVE_ARTICULATION_TRIAL
ROUTE_B_PREREGISTER_BOUNDED_TRANSLATION_PLUS_ACTIVE_ARTICULATION_TRIAL
ROUTE_C_AUDIT_ALTERNATE_SAME_RUN_HAND_CANDIDATES
ROUTE_C_AUDIT_ALTERNATE_CANDIDATES_FULL_HAND_UPPER_BOUND_ONLY
HOLD_PROBE_CONTRADICTS_REGISTERED_BRANCH_E
HOLD_IDENTITY_OR_CONFIGURATION_FAILURE
HOLD_FINITE_DIFFERENCE_NUMERICAL_INSTABILITY
```

## 5. Make the requested visual panel

```bash
python "$TOOL_ROOT/scripts/make_articulation_diagnostic_panel.py" \
  --preflight-dir "$AUDIT_ROOT/preflight" \
  --analysis-dir "$AUDIT_ROOT/analysis" \
  --image /ABS/PATH/to/exact_target_raster.png \
  --out "$AUDIT_ROOT/visuals/articulation_span_panel.png"
```

This panel shows only the zero projection and linearized predicted keypoint motion. It is not an optimized mesh result.

## What happens after the route

### Route A

Preregister one selected-joint articulation trial. Keep root translation and root rotation fixed initially. Use strong pose priors and a silhouette anti-regression gate. Contact/collision remain off.

### Route B

Preregister one joint root-translation plus selected-articulation trial. Use the exact Branch-E radius, keep root rotation fixed, and reject any solution that saturates the trust region.

### Route C

Audit all same-run HaMeR candidates with exact candidate index, handedness, crop/raster transform, keypoints, and silhouette. A VLM may act only as a secondary indexed semantic critic.

### Whole-laptop Route D

Not decided by this toolkit. It becomes eligible only after a source-faithful hand candidate passes the target-image keypoint/silhouette gate and the remaining error is specifically hand-relative laptop composition. Apply one similarity transform to the complete lid/base assembly; never transform parts independently.
