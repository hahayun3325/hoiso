# H0 `alapuse02v3n60` completion, challenges, file map, and handoff

## Status and scope

The authorized bounded H0 diagnostic completed successfully: five global-hand
rotation/translation updates were attempted and accepted, every gate passed,
no rollback occurred, and five checkpoints were written. H0 is now spent and
closed. This document does not claim numerical convergence or final visual
acceptance, and it does not claim completion of H1, O0, J0, or D1.

The case remained ground-truth-free: object geometry came from the accepted
auto-v2/Gate-A lineage, D0 supplied index/middle contact evidence and r04
support, and no dataset category label was used as an optimization target.

## Final quantitative result

- Attempted/accepted updates: `5/5`
- Rollback: `false`
- Initial pre-step total loss: `555.365112`
- Final post-step total loss: `540.566711`
- Relative total-loss change: `-2.665%`
- Step-1 to step-5 base loss: `549.124939` → `537.327148`
- Step-1 to step-5 contact XY: `0.525368` → `0.519597`
- Step-1 to step-5 contact Z: `2.188650` → `2.182214`
- Step-1 to step-5 z-order: `2.160067` → `2.150938`
- Fixed object-depth support: `26144` pixels
- Final positive hand-depth support: `82356` pixels
- Final nonexempt z-order support: `6728` pixels
- Peak allocated GPU memory: `9.185` GiB
- Visual status: `read_only_renderer_pending`

## Architecture that ultimately worked

`D0 evidence/config → case manifest → case callback factory → live Phase-1
callback seam → exact R/t binder → ten-hook runtime → transactional H0
controller → post-update gate → checkpoint/capture`

The callback receives the exact live `rotation_hand` and `trans_hand` tensor
objects. Scale, MANO base/articulation, object pose/geometry/depth, camera, and
observations remain frozen. `handled=True` prevents the legacy hand optimizer
from applying a second update.

## Main challenges and resolutions

1. **False controller-API extraction.** Substring matching misclassified
   `RuntimeError` and the loader as runtime methods. Typed AST inspection
   recovered the real protocol.
2. **Private Phase-1 entrypoint.** The trainable tensors and render/loss owners
   were locals inside the production hand loop. A default-disabled synchronous
   callback seam exposed them without changing the legacy `None` path.
3. **Transaction safety.** Pre-update metrics, missing backward-only mode,
   zero-gradient acceptance, and incomplete rollback were corrected with a
   versioned controller, post-update recomputation, nonzero-gradient guards,
   snapshots, and restoration.
4. **Value versus trainability state.** `requires_grad` was initially mixed
   into the value digest. Separate value and flag ledgers made intentional H0
   enablement compatible with frozen-state verification.
5. **Double-step risk.** The callback's `handled=True` result skips the entire
   legacy hand loop so only the transactional controller owns H0 updates.
6. **Signature and test-shape incidents.** Existing `**kwargs`, the missing
   bare `*`, ordered-list parameter selection, project import paths, and raw
   result versus receipt schemas were each corrected and independently tested.
7. **Dense evidence ownership.** Base dense depth and r04 expansion belonged to
   separate accepted artifacts; binding them by their own hashes closed the
   mistaken cross-generation packet predicate.
8. **Tracked patch versus active runtime.** The canonical patch lived under
   `third_party_patches`, while production imported `third_party/Hunyuan3D-2`.
   A surgical, hash-pinned deployment and active-import test ensured the real
   runtime contained the callback.
9. **OOM and unnecessary legacy tail.** The wrong active runtime continued
   through object/joint optimization and final octree extraction. Early H0
   diagnostic termination plus `cudaMallocAsync` and the 192 octree fallback
   reduced peak allocation to about 9.18 GiB.
10. **Hidden CUDA child environment.** A previous worksheet hid the GPU from
    its child. The final launch probed the exact child environment before each
    GPU action.
11. **Ambiguous zero z-order support.** Additional overlap counts separated
    candidates, positive depth domains, exemptions, and valid support.
12. **Signed-depth mismatch.** The live renderer uses positive camera-view Z,
    but the binder had negated it. Commit `b48fde7` corrected the binder and CPU
    fixture, activating valid hand/object depth comparison.

Residual nonblocking issues: several legacy debug-export paths are absent and
one pre-callback invalid-mesh warning remains. They did not affect the H0
callback result, but should be cleaned separately rather than hidden.

## Necessary project files

- `src/foho/guidance/run_d0_h0_transactional_v99_11_7_13_3_13_5_5_1_7_3_5_14_77.py`
- `src/foho/guidance/h0_live_phase1_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14_77.py`
- `src/foho/guidance/h0_live_callback_dispatch_v99_11_7_13_3_13_5_5_1_7_3_5_14_83.py`
- `src/foho/guidance/h0_case_callback_factory_v99_11_7_13_3_13_5_5_1_7_3_5_14_84.py`
- `src/foho/guidance/h0_metric_face_depth_v99_11_7_13_3_13_5_5_1_7_3_5_14_85.py`
- `src/foho/guidance/h0_complete_hook_bundle_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_1_1.py`
- `src/foho/guidance/h0_callback_launch_bridge_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_1.py`
- `src/foho/guidance/h0_manifest_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_9.py`
- `src/foho/guidance/h0_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_4.py`
- `src/foho/guidance/run_alapuse02v3n60_d0_h0_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_2.py`
- `src/foho/guidance/run.py`
- `tools/hoiso_d0_objective_contract/phase_config_loader.py`
- `tools/hoiso_d0_objective_contract/dense_raster_schedule.py`
- `tools/hoiso_d0_objective_contract/dense_valid_zorder.py`
- `config/optimization/H0_global_dimensionless_loss_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_4.json`
- `third_party_patches/hy3dgen/shapegen/pipelines.py`
- `third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py`
- `tests/hoiso_d0_objective_contract/test_transactional_H0_and_live_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14_77.py`
- `tests/hoiso_d0_objective_contract/test_H0_default_disabled_callback_v99_11_7_13_3_13_5_5_1_7_3_5_14_83.py`
- `tests/hoiso_d0_objective_contract/test_H0_case_callback_factory_v99_11_7_13_3_13_5_5_1_7_3_5_14_84.py`
- `tests/hoiso_d0_objective_contract/test_H0_metric_face_depth_v99_11_7_13_3_13_5_5_1_7_3_5_14_85.py`
- `tests/hoiso_d0_objective_contract/test_H0_complete_hook_bundle_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_1_1.py`
- `tests/hoiso_d0_objective_contract/test_H0_callback_launch_bridge_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_1.py`
- `tests/hoiso_d0_objective_contract/test_H0_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_4.py`

The file under `third_party_patches` is the canonical reviewed source. The file
under `third_party/Hunyuan3D-2` is the active runtime deployment and must always
be verified by import path and SHA256 before execution.

## Case receipts and outputs

- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_positive_view_depth_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_86_8/config/alapuse02v3n60_H0_call_arguments_v99_11_7_13_3_13_5_5_1_7_3_5_14_86_8.json`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_positive_view_depth_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_86_8/reports/H0_positive_view_depth_launch_readiness_v99_11_7_13_3_13_5_5_1_7_3_5_14_86_8.json`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_positive_view_depth_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_86_8/reports/H0_backward_only_preflight_v99_11_7_13_3_13_5_5_1_7_3_5_14_86_8.json`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_capture_zero_and_unlock_v99_11_7_13_3_13_5_5_1_7_3_5_14_87_4/reports/H0_capture_zero_integrity_v99_11_7_13_3_13_5_5_1_7_3_5_14_87_4.json`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_capture_zero_and_unlock_v99_11_7_13_3_13_5_5_1_7_3_5_14_87_4/reports/H0_five_update_unlock_v99_11_7_13_3_13_5_5_1_7_3_5_14_87_4.json`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_five_update_v99_11_7_13_3_13_5_5_1_7_3_5_14_88_4/reports/H0_one_diagnostic_spend_v99_11_7_13_3_13_5_5_1_7_3_5_14_88_4.json`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_five_update_v99_11_7_13_3_13_5_5_1_7_3_5_14_88_4/reports/H0_five_update_launcher_raw_v99_11_7_13_3_13_5_5_1_7_3_5_14_88_4.json`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_five_update_v99_11_7_13_3_13_5_5_1_7_3_5_14_88_4/reports/H0_five_update_review_v99_11_7_13_3_13_5_5_1_7_3_5_14_88_4.json`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_alignment_metrics_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_4/reports/H0_trajectory_metrics_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_4.csv`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_alignment_metrics_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_4/reports/H0_alignment_and_metrics_packet_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_4.json`

The five accepted checkpoints are listed in `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_alignment_metrics_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_4/reports/H0_alignment_and_metrics_packet_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_4.json`.

## Reusable lessons for H1, O0, and J0

- Reuse the transactional controller pattern, callback seam, launcher modes,
  source/hash receipts, rollback, capture, and memory guards.
- Give every phase an exact ordered trainable allowlist and a phase-scoped
  frozen ledger.
- H1 still needs the exact live MANO articulation/joint owner and joint-limit,
  pose-prior, nonselected-finger, and self-collision checks.
- O0 must reraster the moving object after every tentative update and again
  before its post-update gate.
- J0 must coordinate both sides, reraster current geometry, and prevent
  common-mode drift.
- D1 remains a read-only jury over the final reconstruction.

## Immediate handoff

Implement a read-only checkpoint replay. In one fresh process, reconstruct the
pinned Phase-1 state, render the initial state, copy the accepted step-5 R/t
into the ephemeral live tensors, render the final state, and exit without
backward, optimizer construction, checkpoint writing, or mutation of frozen
owners. Export original-crop silhouette, normal, contact/r04, metric-depth, and
z-order overlays for human H0 acceptance before H1 begins.
