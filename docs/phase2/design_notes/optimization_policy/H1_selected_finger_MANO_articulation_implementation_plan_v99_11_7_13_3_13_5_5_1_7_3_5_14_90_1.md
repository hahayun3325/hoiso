# H1 selected-finger MANO articulation implementation plan

## Status and authority

The corrected five-update H0 run for `alapuse02v3n60` is complete and
human-accepted.  H1 remains source-only and locked.  This document defines the
implementation and validation route; it does not authorize an H1 backward
pass or optimizer update.

## H1 purpose

H0 moved the whole hand through global rotation and translation.  H1 keeps
that accepted global pose fixed and refines only the D0-selected index/middle
finger articulation needed for local contact.  H1 does not directly optimize
arbitrary vertex coordinates: it must optimize an explicitly proven subset of
the live MANO articulation parameterization, then let MANO produce the mesh.

## Accepted H0 handoff

- corrected hand triplet: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_intermediate_Hshape_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_10_2/config/corrected_H0_hand_source_triplet_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_10_2.json`
- corrected call arguments: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_intermediate_Hshape_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_10_2/config/alapuse02v3n60_corrected_H0_call_arguments_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_10_2.json`
- accepted H0 checkpoint: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_corrected_five_update_v99_11_7_13_3_13_5_5_1_7_3_5_14_88_7_1/runtime/controller/checkpoints/H0_step_005.pt`
- H0 trajectory metrics: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_corrected_final_evaluation_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_10_5/reports/corrected_H0_trajectory_metrics_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_10_5.csv`
- accepted final panel: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_corrected_final_evaluation_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_10_5/artifacts/alapuse02v3n60_corrected_H0_final_hand_laptop_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_10_5.png`
- human acceptance: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_final_accept_and_H1_plan_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_1/config/corrected_H0_final_human_ACCEPT_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_1.json`

The active source of truth is `/home/fredcui/Projects/FollowMyHold/third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py`.  The reusable
H0 transaction/binding machinery is anchored by `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/h0_manifest_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_9.py`
and `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/run_alapuse02v3n60_d0_h0_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_2.py`.  H1 may reuse their callback, receipt,
rollback, capture, and launch patterns, but it must not reuse H0's hard-coded
global-R/T parameter allowlist unchanged.

## Direct blocker: exact live MANO articulation owner

Before source editing, prove all of the following from the active production
call graph:

1. one live differentiable MANO pose/articulation tensor is used to construct
   the hand mesh at the H1 seam;
2. its shape, joint ordering, axis/rotation representation, handedness, and
   value units are explicit;
3. D0-selected index/middle joints map to an ordered subset of this tensor;
4. gradients from selected pad vertices reach exactly the permitted pose
   dimensions;
5. global R/T, scale, wrist/root, nonselected fingers, hand shape/betas,
   object, camera, and observations remain frozen.

Names such as `mano_verts` or `joint_optimizer` are candidates, not proof of a
trainable leaf.  A generated mesh tensor is not automatically the correct
optimization owner.

## Trainable and frozen state

Trainable in H1:

- only the ordered MANO pose dimensions proven to control the D0-selected
  index/middle articulation;
- optimizer state belonging to those exact tensor identities.

Frozen in H1:

- accepted H0 global hand rotation and translation;
- hand scale, wrist/root orientation, MANO shape/betas, and nonselected joint
  values;
- Gate-A laptop geometry and pose, dense depth/valid/face packets, `r04`
  support, camera, image observations, and case hashes.

Because MANO is kinematically coupled, “selected fingers only” must be tested
with a Jacobian/support audit and nonselected-vertex drift bounds; it cannot be
assumed from parameter names.

## H1 objective

Recompute every active term from the current articulated hand:

- existing differentiable base observation loss;
- selected index/middle pad-to-`r04` contact-XY and contact-Z losses;
- dense-valid metric z-order and collision/penetration terms;
- MANO pose prior and anatomical joint-limit penalties;
- self-collision and nonselected-finger/palm integrity penalties;
- a trust region around the accepted initial H1 articulation.

Weights belong in one global dimensionless H1 policy, not in the per-case
manifest.  The auto-v2/D0 receipts select evidence and active parts; they do
not authorize ground-truth category labels or a new object-pose selector.

## Transaction and memory contract

Each tentative update snapshots parameter values, trainability flags,
optimizer state, scheduler state if present, and required RNG state.  Losses
and gates are rerendered after the tentative update.  Rejection or exception
restores the complete snapshot.  The fixed laptop raster is loaded/hash-checked
once for H1; the hand is rerendered per loss/gate call.  Use the established
CUDA allocator and early diagnostic callback so final high-resolution object
extraction is not reached during H1 diagnostics.

## Planned repository targets

These are future targets and are intentionally allowed to be absent during
this planning worksheet:

- `/home/fredcui/Projects/FollowMyHold/config/optimization/H1_selected_finger_dimensionless_loss_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_2.json`
- `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/h1_selected_finger_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_2.py`
- `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/run_alapuse02v3n60_d0_h1_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_2.py`
- `/home/fredcui/Projects/FollowMyHold/tests/hoiso_d0_objective_contract/test_H1_selected_finger_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_2.py`

The active pipeline should receive only the smallest default-disabled H1 seam
needed to expose the real context.  Reusable H1 logic belongs under
`src/foho/guidance`; case IDs and artifact hashes belong in a case manifest
under the case root.

## Validation ladder

1. CPU/source owner audit: exact live leaf identity, shape, ordered joint map,
   active source hash, and default-disabled equivalence.
2. CPU differentiability fixture: selected joint dimensions have finite
   nonzero gradients; forbidden dimensions and frozen values remain unchanged.
3. CPU transactional fixture: no double step, post-update recomputation,
   rejection/exception rollback including optimizer state, non-overwrite.
4. Real GPU backward-only: zero updates, exact selected gradient owners,
   selected contact/depth/z-order terms active, frozen digest unchanged.
5. Separate capture-only replay: zero gradients, updates, and checkpoints;
   then issue one immutable H1 five-update unlock.
6. Exactly five bounded H1 attempts with accepted/rejected trajectory,
   checkpointing, rollback, and peak-VRAM receipt.
7. Read-only before/after panel and metrics review.  Proceed to O0 only after
   human acceptance.

## H1 outputs and acceptance

The H1 evaluation packet must include the initial/final articulated hand over
the input and fixed laptop, selected pad/`r04` support, contact-XY/contact-Z,
z-order/penetration, base observation loss, pose prior, joint-limit and
nonselected-drift metrics, per-joint deltas, accepted/rejected steps, frozen
digests, checkpoints, source/input hashes, and peak GPU memory.

H1 passes only if the selected-finger contact is visibly and numerically
improved without moving accepted H0 global R/T, damaging nonselected hand
regions, penetrating the laptop, or violating rollback/frozen-state policy.

## Parametric-owner correction — 14_90_2


The scope-aware active-source audit proved that production currently loads a
fixed 778-vertex PLY and does not expose a live MANO pose/shape layer.  H1 must
therefore recover or regenerate the exact HaMeR parameter carrier and bind it
to a hash-pinned MANO provider before implementing the selected residual.
`mano_verts`, keypoint mappings, and the generic legacy `joint_optimizer` are
not accepted articulation owners.  The normative ownership and file-map
contract is `/home/fredcui/Projects/FollowMyHold/docs/phase2/design_notes/optimization_policy/H1_MANO_articulation_ownership_contract_and_file_map_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_2.md`.
