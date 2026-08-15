# Professor’s Answer: `alapuse02v3n60` Automatic Recovery and VLM Failure Containment

**Project:** HOISO-Flow Phase 2.1
**Case:** `alapuse02v3n60`
**Positive reference:** `alapuse02v6n60`
**Reviewed branches:** E/H2, G, H, I, J, K
**Decision:** Continue one bounded **method-level automatic branch**, while freezing Candidate I as an oracle and closing Candidate K
**Date:** July 2026

---

## 1. Professor’s decision

I do **not** recommend treating Candidate I as the end of the research question. The supplied panel shows that Candidate I gives the strongest laptop-only input and that its fixed-seed Hunyuan outputs recover the previously missing base corner. That is important evidence that the downstream generator can produce a materially better laptop when the silhouette is correct.

However, Candidate I was constructed from a human-reviewed full silhouette. It is therefore an **oracle upper bound**, not an automatic recovery result.

I also do **not** recommend another synonym-level modification of Candidate K. Candidate K has already answered its scientific question:

- language-only segmentation of “wooden stand” is insufficient;
- the model selected the visually dominant tabletop;
- the automatic target proposal still contains the support;
- the schema and fail-closed router correctly prevented unsafe downstream use.

The correct next step is:

> **Close Candidate K, but open one new pre-registered automatic method called AUTO-V2: part-aware spatial grounding + box-prompted segmentation + deterministic candidate composition + AGILE-style VLM rejection.**

This is not “Candidate L” in an endless repair chain. It is a new method class with a fixed candidate bank and a hard stopping rule.

Use `alapuse02v3n60` as the **development case**. Any automatic-recovery claim must then be repeated without threshold or prompt changes on held-out cases.

---

## 2. Reading of the two new panels

### Candidate I panel

The panel supports four conclusions:

1. The laptop-only mask contains the full lid and base silhouette.
2. The Hunyuan input is a proper three-channel, white-background RGB asset.
3. The support and tabletop are absent from the proposed object asset.
4. The resulting Hunyuan meshes recover the missing base corner more successfully than H2.

This is a valid **oracle ceiling** for mask recovery and downstream object generation. It must remain labelled:

```text
human_reviewed_oracle
oracle_upper_bound
excluded_from_automatic_success_metrics
```

### Candidate K panel

The panel also supports four conclusions:

1. The failed automatic laptop mask still merges the target with its support.
2. The failed RGB proposal therefore contains non-target structure.
3. The supposed “wooden stand” mask selects the large tabletop rather than the small support below the laptop.
4. Blocking Hunyuan was correct.

Candidate K is not evidence that VLM failure containment failed. It is evidence that **candidate generation failed while containment succeeded**.

---

## 3. Answers to the inquiry questions

### Q1. Should the automatic branch be closed for this case?

**Close Candidate K, but do not close automatic-recovery research yet.** Authorize one bounded AUTO-V2 method-level experiment. No further prompt-synonym tuning of K is allowed.

### Q2. May Candidate I be used?

**Yes, only as an oracle.** It may be used for:

- downstream plumbing;
- fixed-seed Hunyuan comparison;
- evaluation-only mask IoU and boundary F1;
- illustrating the attainable upper bound.

It may not provide pixels, polygon coordinates, boxes, masks, or mesh geometry to AUTO-V2.

### Q3. Is failure containment alone a sufficient contribution?

It is a useful and publishable **supporting result**, but it is not yet the main recovery contribution. The defensible result is:

> The fail-closed critic/router prevents unsafe and provenance-invalid inputs from reaching Hunyuan.

For an automatic-recovery claim, the project still needs an automatically constructed target asset that passes the same gates.

### Q4. Should automatic recovery be developed on this image or only on held-out images?

Use `alapuse02v3n60` as the development case because it exposes the exact failure. Freeze the method before held-out evaluation. Report development and held-out results separately.

### Q5. Which automatic method should be tried next?

Use the following combination:

```text
spatial VLM proposal
→ box-prompted SAM2 masks for lid/base/support/table
→ fixed part-aware candidate bank
→ deterministic contamination/topology checks
→ blind VLM critic
→ exact-file authorization
→ one fixed-seed Hunyuan run
```

This is preferable to another whole-object language prompt because the failure requires distinguishing:

```text
laptop lid
laptop base
wooden support
white tabletop
```

### Q6. May `alapuse02v6n60` be reused?

Reuse only its **semantic part schema**:

```text
lid/screen
keyboard base
hinge relation
```

Do not use its pixels, mask coordinates, part meshes, silhouette, pose, or dimensions in the main automatic branch. A template-guided variant would be a separate ablation.

### Q7. Should the manual VLM advisory remain in the automatic route?

Only as a development bridge. The raw response must be saved without editing and mechanically validated. A fully automatic success claim requires the same prompt and schema to be called through an API or local VLM wrapper without human modification.

### Q8. Should human-reviewed geometry be excluded from automatic metrics?

**Yes.** Candidate I is excluded from automatic success rate and included in a separate oracle column.

### Q9. What is the next milestone?

The immediate milestone is a new pre-Hunyuan gate:

> **Gate R-AUTO:** at least one automatically constructed candidate preserves the complete laptop, excludes support/table/hand, passes deterministic topology checks, and passes one blind VLM critic.

Only after Gate R-AUTO passes should Hunyuan and later Gate A/B/C/D be run.

### Q10. What is the stopping rule?

Use this fixed rule:

```text
one spatial proposal
one SAM2 configuration
at most four deterministic candidates
one blind critic query
one selected fixed-seed Hunyuan run

If no candidate passes:
  record AUTO-V2 failure;
  freeze further tuning on v3n60;
  revise the method only at multi-case level.
```

No fifth candidate, manual ROI, edited VLM response, or post-result threshold change is allowed.

---

## 4. Why AUTO-V2 follows the related works

### FollowMyHold lesson: repair before reconstruction

FollowMyHold’s staged optimization is effective only after a usable object hypothesis exists. Its own failure analysis shows that segmentation and inpainting errors propagate into the reconstructed object. Therefore, a support-contaminated asset must be rejected or repaired before Hunyuan rather than delegated to contact or collision optimization.

### ArtHOI lesson: parts and structured priors

ArtHOI treats articulated objects as named parts and uses structured semantic output rather than one unconstrained whole-object guess. The direct adaptation here is to segment the laptop lid and base independently, then enforce the lid-base relation. PartField is relevant after 3D generation, but the immediate 2D recovery problem should start with explicit part masks.

### AGILE lesson: candidate generation and criticism are separate

AGILE uses a VLM to supervise candidate generation and rejects inconsistent visual assets before 3D lifting. The VLM should therefore be the critic/router, not the pixel-level mask generator. AUTO-V2 creates a small, fixed candidate bank and applies one critic consistently.

### WHOLE lesson: spatial grounding beats language-only reference

WHOLE improves VLM reliability by displaying indexed masks and enforcing exact validation constraints. The analogous move here is to localize explicit regions—lid, base, support, tabletop—and use box-prompted segmentation, rather than asking a text segmenter to understand the ambiguous phrase “wooden stand.”

### ForeHOI lesson: 2D and 3D completion should communicate

ForeHOI jointly learns 2D mask completion and 3D shape completion. Reproducing its trained network is outside the immediate scope, but its principle should be used as a post-Hunyuan consistency test: the rendered 3D silhouette must agree with the selected automatic 2D mask. Do not use the Hunyuan render to silently rewrite the mask in this first experiment, because that would create a self-confirming loop.

---

## 5. AUTO-V2 pipeline

## Stage A — Spatially grounded region proposal

The VLM receives only `contextual_inpaint.png` and returns normalized boxes for:

```text
whole_laptop
laptop_lid
laptop_base
wooden_support
tabletop
```

The response is raw JSON under a fixed schema. The VLM does not authorize Hunyuan and does not draw a silhouette.

## Stage B — Box-prompted SAM2 segmentation

Run SAM2 separately for each box. This makes the segmentation question spatial rather than linguistic.

## Stage C — Fixed candidate bank

Generate no more than four candidates:

| Candidate | Construction | Purpose |
|---|---|---|
| `c01_whole_minus_distractors` | whole-laptop mask minus support/table masks | tests whole-object segmentation with explicit distractor removal |
| `c02_part_union_raw` | lid union base | pure ArtHOI-style part composition |
| `c03_part_union_minus_distractors` | lid/base union after support/table subtraction | main conservative candidate |
| `c04_part_graph_complete` | constrained automatic convex completion of lid/base | recovers open boundaries without manual points |

## Stage D — Deterministic gate

A candidate is not shown to Hunyuan unless it satisfies all registered checks:

- lid retention at least `0.90`;
- base retention at least `0.90`;
- support overlap at most `0.005`;
- tabletop overlap at most `0.005`;
- largest-component fraction at least `0.85`;
- at most three connected components;
- lid centroid above base centroid;
- lid and base connect within the registered hinge tolerance;
- negligible contact with the bottom image border.

## Stage E — Blind VLM critic

The critic receives the same three rows per candidate:

```text
overlay
binary mask
exact Hunyuan RGB
```

It evaluates identity, complete lid/base, hinge, support absence, tabletop absence, hand absence, and orientation. The local router—not the VLM—selects the highest-confidence candidate that also passed the deterministic gate.

## Stage F — Existing exact-file authorization

Reuse the current provenance guard and authorization wrapper. AUTO-V2 preselection is not authorization.

## Stage G — One fixed-seed Hunyuan run

Run only the selected exact RGB file with the registered settings:

```text
steps=30
resolution=384
num_chunks=8000
seed=1234
```

## Stage H — Post-Hunyuan review

Require:

- recognizable open laptop;
- no house-like support or tabletop extrusion;
- lid and base both present;
- hinge relation preserved;
- no worse corner loss than H2;
- rendered silhouette consistent with the selected automatic mask.

---

## 6. Necessary commands

A ready-to-use toolkit accompanies this answer. Place it on the RTX 4090 desktop at:

```text
/home/fredcui/Projects/FollowMyHold/tools/auto_v2_part_graph
```

### Step 1 — install and bootstrap the method-level branch

```bash
cd /home/fredcui/Projects/FollowMyHold
source /home/fredcui/anaconda3/etc/profile.d/conda.sh
conda activate foho

mkdir -p tools/auto_v2_part_graph
cp -a /PATH/TO/alapuse02v3n60_auto_v2_toolkit/. \
  tools/auto_v2_part_graph/

bash tools/auto_v2_part_graph/bootstrap_auto_v2.sh
```

The bootstrap creates:

```text
/home/fredcui/foho_phase0/vlm_failure_containment/alapuse02v3n60/
  inpainting_fallback/automatic_recovery_v2_part_graph/
```

It also writes the fixed pre-registration and source inventories. It does not run any model.

### Step 2 — inspect source paths and SAM2 capability

```bash
export AUTO_V2='/home/fredcui/foho_phase0/vlm_failure_containment/alapuse02v3n60/inpainting_fallback/automatic_recovery_v2_part_graph'

cat "$AUTO_V2/source/source_inventory.txt"
bash "$AUTO_V2/review/code_capability_inventory.sh"

cat "$AUTO_V2/review/sam2_asset_inventory.txt"
cat "$AUTO_V2/review/code_capability_inventory.txt"
```

Copy the template and correct only filesystem paths:

```bash
cp -n "$AUTO_V2/source/paths.env.template" "$AUTO_V2/source/paths.env"
nano "$AUTO_V2/source/paths.env"
source "$AUTO_V2/source/paths.env"

for path in "$REFERENCE_RGB" "$CONTEXT_RGB"; do
  if test -s "$path"; then
    echo "[PASS] AUTO_V2_SOURCE=$path"
  else
    echo "[HOLD] AUTO_V2_SOURCE_MISSING=$path"
  fi
done
```

Do not copy any Candidate I coordinate or shape into this file. `ORACLE_MASK_EVAL_ONLY` is used only after selection for metrics.

### Step 3 — obtain one spatial proposal

Use this prompt with `$CONTEXT_RGB`:

```text
tools/auto_v2_part_graph/prompts/spatial_proposal_prompt.md
```

Save the unedited response:

```text
$AUTO_V2/vlm_spatial/raw_response.json
```

Validate it:

```bash
python3 tools/auto_v2_part_graph/validate_spatial_proposal.py \
  "$AUTO_V2/vlm_spatial/raw_response.json" \
  "$CONTEXT_RGB" \
  "$AUTO_V2/vlm_spatial/validated"
```

Expected markers:

```text
[PASS] SPATIAL_PROPOSAL_VALIDATED=...
[PASS] SPATIAL_PROPOSAL_OVERLAY=...
```

Inspect:

```bash
python3 - <<PY
from PIL import Image
Image.open('$AUTO_V2/vlm_spatial/validated/boxes_overlay.png').show()
PY
```

If the response is uncertain, malformed, or boxes the wrong regions, record a hold. Do not edit the raw JSON or requery with synonyms on this case.

### Step 4 — run box-prompted SAM2 once

After setting the real config and checkpoint paths in `paths.env`:

```bash
python3 tools/auto_v2_part_graph/sam2_box_segment.py \
  "$AUTO_V2/vlm_spatial/validated/boxes_px.json" \
  "$CONTEXT_RGB" \
  "$SAM2_CONFIG" \
  "$SAM2_CHECKPOINT" \
  "$AUTO_V2/part_masks" \
  cuda
```

Inspect all overlays:

```bash
find "$AUTO_V2/part_masks" -maxdepth 1 -type f \
  \( -name '*_overlay.png' -o -name '*_mask.png' \) \
  | sort
```

The required outputs are:

```text
whole_laptop_mask.png
laptop_lid_mask.png
laptop_base_mask.png
wooden_support_mask.png
tabletop_mask.png
```

### Step 5 — write the fixed build configuration

```bash
python3 - \
  "$AUTO_V2" \
  "$REFERENCE_RGB" \
  "$CONTEXT_RGB" \
  "${OPTIONAL_WHOLE_MASK:-}" <<'PY'
from pathlib import Path
import json
import sys

root = Path(sys.argv[1])
reference = Path(sys.argv[2])
context = Path(sys.argv[3])
optional_whole = Path(sys.argv[4]) if sys.argv[4] else None
masks = {
    "lid": str(root / "part_masks/laptop_lid_mask.png"),
    "base": str(root / "part_masks/laptop_base_mask.png"),
    "support": str(root / "part_masks/wooden_support_mask.png"),
    "tabletop": str(root / "part_masks/tabletop_mask.png"),
}
if optional_whole and optional_whole.is_file():
    masks["whole"] = str(optional_whole)
config = {
    "case_id": "alapuse02v3n60",
    "reference_rgb": str(reference),
    "context_rgb": str(context),
    "output_root": str(root / "candidate_bank"),
    "masks": masks,
    "thresholds": {
        "distractor_dilate_px": 1,
        "hinge_dilation_px": 8,
        "max_completion_area_gain": 1.35,
        "max_distractor_overlap_fraction": 0.005,
        "max_bottom_border_touch_fraction": 0.02,
        "max_components": 3,
        "min_lid_retention": 0.90,
        "min_base_retention": 0.90
    }
}
out = root / "preregistration/build_config.json"
if out.exists():
    print(f"[HOLD] BUILD_CONFIG_ALREADY_EXISTS={out}")
else:
    out.write_text(json.dumps(config, indent=2) + "\n")
    print(f"[PASS] BUILD_CONFIG_WRITTEN={out}")
PY
```

### Step 6 — build the immutable candidate bank

```bash
python3 tools/auto_v2_part_graph/build_part_graph_candidate_bank.py \
  "$AUTO_V2/preregistration/build_config.json"
```

Inspect the summary and critic panel:

```bash
python3 -m json.tool \
  "$AUTO_V2/candidate_bank/candidate_bank_summary.json" \
  | less

python3 - <<PY
from PIL import Image
Image.open('$AUTO_V2/candidate_bank/critic_candidate_bank.png').show()
PY
```

Candidates failing the deterministic gate remain valid ablations but are not eligible for Hunyuan.

### Step 7 — run one blind VLM critic

Use:

```text
tools/auto_v2_part_graph/prompts/candidate_critic_prompt.md
```

with:

```text
$AUTO_V2/candidate_bank/critic_candidate_bank.png
```

Save the raw response unchanged:

```text
$AUTO_V2/vlm_critic/raw_response.json
```

Run the local router:

```bash
python3 tools/auto_v2_part_graph/select_candidate_from_critic.py \
  "$AUTO_V2/candidate_bank/candidate_bank_summary.json" \
  "$AUTO_V2/vlm_critic/raw_response.json" \
  "$AUTO_V2/selection"

if test -s "$AUTO_V2/selection/selected_candidate.env"; then
  source "$AUTO_V2/selection/selected_candidate.env"
else
  export AUTO_V2_SELECTED='0'
fi

echo "AUTO_V2_SELECTED=${AUTO_V2_SELECTED:-0}"
echo "AUTO_V2_SELECTED_ID=${AUTO_V2_SELECTED_ID:-none}"
```

If `AUTO_V2_SELECTED=0`, stop. That is a valid automatic failure, not permission to create another candidate.

### Step 8 — reuse the existing provenance guard

```bash
export AUTH_ROOT="$AUTO_V2/auth"
export RESPONSE_GUARD_ENV="$AUTH_ROOT/$AUTO_V2_SELECTED_ID.response_guard.env"
export AUTH_ENV="$AUTH_ROOT/$AUTO_V2_SELECTED_ID.inpaint_authorization.env"
mkdir -p "$AUTH_ROOT"

python3 scripts/phase2_1/guard_vlm_inpaint_response.py \
  "$AUTO_V2/vlm_critic/raw_response.json" \
  "$AUTO_V2_SELECTED_MANIFEST" \
  "$AUTO_V2_SELECTED_RGB" \
  "$AUTO_V2_SELECTED_ID" \
  "$RESPONSE_GUARD_ENV"

if test -s "$RESPONSE_GUARD_ENV"; then
  source "$RESPONSE_GUARD_ENV"
else
  export VLM_INPAINT_RESPONSE_PROVENANCE='0'
  export VLM_INPAINT_RESPONSE_PROVENANCE_REASON='response_guard_missing'
fi

if test "$VLM_INPAINT_RESPONSE_PROVENANCE" = '1'; then
  python3 tools/validate_vlm_inpaint_asset.py \
    "$AUTO_V2/vlm_critic/raw_response.json" \
    "$AUTO_V2_SELECTED_DIR" \
    "$AUTH_ENV"
else
  echo "[HOLD] AUTO_V2_AUTH_BLOCKED=$VLM_INPAINT_RESPONSE_PROVENANCE_REASON"
fi
```

The new manifest schema is:

```text
inpaint_fallback_candidate_v7_auto_part_graph
```

If the existing guard rejects only because it has not registered this schema, update the guard code and its tests to accept the new schema. Do not edit the generated manifest or response to bypass the guard.

### Step 9 — run one fixed-seed Hunyuan dry run

```bash
if test -s "$AUTH_ENV"; then
  source "$AUTH_ENV"
else
  export VLM_INPAINT_AUTHORIZED='0'
  export VLM_INPAINT_AUTH_REASON='authorization_missing'
  export VLM_INPAINT_PREFERRED_IMAGE=''
fi

export HUNYUAN_DIR="$AUTO_V2/hunyuan/$AUTO_V2_SELECTED_ID.steps30.octree384.seed1234"
export HUNYUAN_GLB="$HUNYUAN_DIR/repaired_object.glb"
mkdir -p "$HUNYUAN_DIR"

if test "$VLM_INPAINT_AUTHORIZED" = '1' \
  && test "$VLM_INPAINT_PREFERRED_IMAGE" = "$AUTO_V2_SELECTED_RGB" \
  && test -s "$AUTO_V2_SELECTED_RGB"; then

  python3 scripts/phase2_1/run_hunyuan_shape_dryrun.py \
    --image "$AUTO_V2_SELECTED_RGB" \
    --out "$HUNYUAN_GLB" \
    --steps 30 \
    --octree-resolution 384 \
    --num-chunks 8000 \
    --seed 1234 \
    2>&1 | tee "$HUNYUAN_DIR/hunyuan.log"
else
  echo "[HOLD] AUTO_V2_HUNYUAN_BLOCKED authorization=$VLM_INPAINT_AUTHORIZED reason=$VLM_INPAINT_AUTH_REASON image=$VLM_INPAINT_PREFERRED_IMAGE"
fi
```

### Step 10 — compare the automatic mask with the oracle, for evaluation only

```bash
if test -s "$ORACLE_MASK_EVAL_ONLY" \
  && test -s "$AUTO_V2_SELECTED_DIR/repaired_object_mask.png"; then

  python3 tools/auto_v2_part_graph/compare_mask_to_oracle.py \
    "$AUTO_V2_SELECTED_DIR/repaired_object_mask.png" \
    "$ORACLE_MASK_EVAL_ONLY" \
    "$AUTO_V2/evaluation/$AUTO_V2_SELECTED_ID.vs_oracle.json" \
    3
else
  echo "[HOLD] AUTO_V2_ORACLE_METRIC_INPUT_MISSING"
fi
```

This comparison does not contaminate the automatic branch because it occurs after candidate construction and selection.

---

## 7. Success criteria

## Pre-Hunyuan success

```text
one candidate passes deterministic gate
AND
blind critic marks it safe
AND
exact-file authorization passes
```

## Post-Hunyuan success

```text
open laptop identity preserved
complete lid and base present
support/table absent
hinge relation plausible
no new major missing corner
mesh passes post-Hunyuan critic
```

## Scientific success

For the development case:

```text
AUTO-V2 reaches an authorized automatic Hunyuan result
and is closer to Candidate I than H2 on mask IoU/boundary F1
without using Candidate I during construction.
```

For a paper-level claim:

```text
freeze prompts, thresholds, schemas, and candidate count;
repeat on held-out cases;
report success rate, reject rate, unsafe runs blocked,
mask quality, and downstream mesh quality.
```

---

## 8. What not to do next

Do not:

```text
retune “wooden stand” synonyms;
add a manual ROI to K;
copy Candidate I polygon points;
use v6n60 image geometry;
edit raw VLM JSON;
create an unregistered fifth candidate;
run every candidate through Hunyuan;
claim the development case alone demonstrates general recovery.
```

---

## 9. Recommended reporting language

Use:

> Candidate I establishes a human-reviewed oracle ceiling. Candidate K demonstrates that language-only distractor segmentation is insufficient for contact-connected, visually similar support structures. We therefore introduce a bounded automatic recovery branch that uses spatially grounded part localization, box-prompted segmentation, deterministic part-graph candidate construction, and fail-closed VLM rejection before 3D lifting.

Do not use:

> The VLM automatically fixed the mask.

The VLM proposes locations and critiques candidates. The deterministic segmentation/composition branch constructs the pixels.

---

## 10. Final professor recommendation

Proceed with AUTO-V2 now. Keep Candidate I frozen as the oracle and Candidate K frozen as the failed language-only baseline. The next meaningful result is not another prompt; it is whether a fixed part-aware, spatially grounded candidate bank can automatically recover the laptop while the existing critic/router prevents contaminated candidates from reaching Hunyuan.

If AUTO-V2 fails under the registered stopping rule, the case remains a successful containment result and a failed automatic-recovery result. At that point, move method development to a multi-case design rather than continuing to tune `alapuse02v3n60`.
