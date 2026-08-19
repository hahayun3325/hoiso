# J0 alapuse02v3n60 ownership contract and implementation proposal

## Status

Documentation-only. J0 implementation, backward, capture, optimization, and GPU use remain locked.

## Purpose

J0 is a small coupled trust-region refinement after accepted O0. It is not an O0 rerun, not a final judge, and not a VLM jury.

## Authoritative terminal lineage

J0 must consume the O0-resolved live context. The three checkpoints below form one immutable lineage and are not independently selectable:

- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_corrected_five_update_v99_11_7_13_3_13_5_5_1_7_3_5_14_88_7_1/runtime/controller/checkpoints/H0_step_005.pt`
  - SHA256: `8e382d5f712e520970e558d3c8cedf158d65e2281afc6ed99e4fd02cac926eb6`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_fixed_registration_five_attempt_v99_11_7_13_3_13_5_5_1_7_3_5_14_93_2/runtime/controller/checkpoints/H1_attempt_005.pt`
  - SHA256: `f21a0ac081d6eb282f9d77e610faa99367f7d6174c1ca3a1d8399f956d482f4b`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_O0_five_attempt_v99_11_7_13_3_13_5_5_1_7_3_5_14_98/runtime/controller/checkpoints/O0_attempt_005.pt`
  - SHA256: `b6a5adf128be9a3bec622bc5d23c590942d7b137984f5879d75f2aed9ed86a64`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_fixed_registration_final_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_7/reports/H1_final_panel_human_ACCEPT_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_7.json`
  - SHA256: `e10c4bd009865ba77995b86d55ecf86f49b25e3cfc4060318cc814f416e4248d`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_O0_human_closure_and_J0_handoff_v99_11_7_13_3_13_5_5_1_7_3_5_14_99_3/reports/O0_human_final_review_v99_11_7_13_3_13_5_5_1_7_3_5_14_99_3.json`
  - SHA256: `049170e04a713db5890355899e5b8df2734d219e6ddb3144fdf7c74d3b5da92c`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_O0_evaluation_v99_11_7_13_3_13_5_5_1_7_3_5_14_99/reports/O0_trajectory_and_metric_delta_v99_11_7_13_3_13_5_5_1_7_3_5_14_99.json`
  - SHA256: `beec67bc6227b32d8219606189cd5c11cb2b37d3625e17f5854e55b0d5ad824d`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_O0_same_camera_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_99_2_5/panels/alapuse02v3n60_O0_same_camera_fixed_H1_hand_initial_final_laptop_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_99_2_5.png`
  - SHA256: `ad2551e1798cea8b795ff0aab106ff2e7fa237beb7a999517276be95402d34da`
- `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/h0_manifest_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_9.py`
  - SHA256: `452f4252fdd424cb0a13ecd287875330b16ef4240f750e6f10e2f2ac5f3c1eeb`
- `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/h1_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_5.py`
  - SHA256: `125c1db6eb47de3235205f76d07ed0a10686386459bb39f51acb2073e15f8a3e`
- `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/h1_selected_finger_mano_provider_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_4.py`
  - SHA256: `b87cf43dfb3b66e66f6ea6dd5b230352a99705480fba7106bd05180c33343f60`
- `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/o0_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3.py`
  - SHA256: `89556a8dfb9642e3f7c87c8669d2bbf0eb7b54e68a545c5d7fb5b1ecbc1a72d2`
- `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/o0_transactional_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3.py`
  - SHA256: `f7e5e19a393d69d3a677adb4707b6f38f3541c3bad227a931e3564090a19a773`
- `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/h0_live_callback_dispatch_v99_11_7_13_3_13_5_5_1_7_3_5_14_83.py`
  - SHA256: `cc620f7436300f025367e6c12a2cde9b815de64cd686228e08bb4ee7c6fdbcb2`
- `/home/fredcui/Projects/FollowMyHold/third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py`
  - SHA256: `0eabad456a90763e1d940424ed9dc966738cf00c0989276de10e6889de5fa05d`
- `/home/fredcui/Projects/FollowMyHold/third_party_patches/hy3dgen/shapegen/pipelines.py`
  - SHA256: `efe3173c8597563bd03451f2c5884b9f449eeb827d14f0d7981d4ec8e5345403`

## Exact canonical variable contract

The public names, order, owners, and observed shapes are:

- `global_hand_rotation`
  - direct checkpoint owner: `H0`
  - artifact: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_corrected_five_update_v99_11_7_13_3_13_5_5_1_7_3_5_14_88_7_1/runtime/controller/checkpoints/H0_step_005.pt`
  - observed shape: `[[4]]`
- `global_hand_translation`
  - direct checkpoint owner: `H0`
  - artifact: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_corrected_five_update_v99_11_7_13_3_13_5_5_1_7_3_5_14_88_7_1/runtime/controller/checkpoints/H0_step_005.pt`
  - observed shape: `[[3]]`
- `selected_so3_residual`
  - direct checkpoint owner: `H1`
  - artifact: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_fixed_registration_five_attempt_v99_11_7_13_3_13_5_5_1_7_3_5_14_93_2/runtime/controller/checkpoints/H1_attempt_005.pt`
  - observed shape: `[[6, 3]]`
- `global_object_rotation`
  - direct checkpoint owner: `O0`
  - artifact: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_O0_five_attempt_v99_11_7_13_3_13_5_5_1_7_3_5_14_98/runtime/controller/checkpoints/O0_attempt_005.pt`
  - observed shape: `[[4]]`
- `global_object_translation`
  - direct checkpoint owner: `O0`
  - artifact: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_O0_five_attempt_v99_11_7_13_3_13_5_5_1_7_3_5_14_98/runtime/controller/checkpoints/O0_attempt_005.pt`
  - observed shape: `[[3]]`

The global hand R/t owner is corrected H0; H1 inherits those values and directly owns only `selected_so3_residual`; O0 directly owns object R/t. The binders must resolve this chain before J0 receives live tensor references.

Forbidden parameter aliases: `hand_R`, `hand_t`, `object_R`, `object_t`, `R`, `t`, `rot`, `trans`, and `pose_delta`.

## Callback and joint-seam owner

The existing O0 seam has the exact public argument `o0_live_callback` and calls `dispatch_h0_live_callback(o0_live_callback, _o0_context)`. J0 must not rename or repurpose that O0 argument. The proposed new public argument is exactly `j0_live_callback`; it must default to `None`, be forwarded once to the audited dispatcher surface, and be inserted at the structurally proven legacy-joint entry before legacy optimizer construction. Whole-file line numbers are not the contract; AST owner, exact argument spelling, and semantic order are.

Forbidden callback aliases: `joint_callback`, `joint_live_callback`, `j0_callback`, and reuse of `o0_live_callback` for J0.

## Candidate trainable and frozen state

The five canonical values are only the maximum CPU-test candidate. The implementation may narrow this allowlist but must never broaden or rename it. Hand shape, nonselected MANO pose, hand/object scale and topology, camera/FOV, D0 semantic targets, r04 map, and all source/input hashes stay frozen.

## Loss and update semantics

Rerasterize both accepted bodies after every proposal. Image, contact, depth, z-order, and r04 objectives couple the scene. Trust-region terms anchor hand variables to accepted H0/H1 and object variables to accepted O0. A rejected gate restores all live values, flags, optimizer state, and checkpoint lineage atomically.

## Proposed source targets

- `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/j0_transactional_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14_100_2.py`
- `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/j0_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_100_2.py`
- `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/run_alapuse02v3n60_d0_j0_v99_11_7_13_3_13_5_5_1_7_3_5_14_100_2.py`
- `/home/fredcui/Projects/FollowMyHold/config/optimization/alapuse02v3n60_J0_case_manifest_v99_11_7_13_3_13_5_5_1_7_3_5_14_100_2.json`
- `/home/fredcui/Projects/FollowMyHold/config/optimization/J0_joint_trust_region_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_100_2.json`
- `/home/fredcui/Projects/FollowMyHold/tests/hoiso_d0_objective_contract/test_J0_three_checkpoint_live_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_100_2.py`
- `/home/fredcui/Projects/FollowMyHold/tests/hoiso_d0_objective_contract/test_J0_transactional_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14_100_2.py`

The active and tracked pipeline files are potential seam targets only after candidate construction, AST selection, CPU integration proof, and runtime-import equivalence. They are not authorized for immediate editing by this note.

## Required CPU acceptance

1. Resolve the exact H0 -> H1 -> O0 lineage and hashes.
2. Identity reconstruction reproduces accepted hand and object vertices.
3. Tensor objects exposed to J0 are the canonical live owners, not copies.
4. Jacobians are finite/nonzero only for the approved subset.
5. Frozen values and hashes remain bitwise unchanged.
6. Rejection atomically restores the complete coupled state.
7. Save/load reproduces all accepted variables and lineage.
8. The active imported seam matches the audited AST owner.

## Guarded execution ladder

1. Build candidates without editing live source.
2. Audit, deploy transactionally, compile, and run CPU tests.
3. Commit and push only the passing source set.
4. J0 backward-only with finite gradients and zero updates.
5. Capture-only with identical hashes and zero state change.
6. Issue one immutable bounded-run unlock.
7. Run one bounded five-attempt J0 optimization.
8. Audit attempts, checkpoints, rollback, frozen hashes, and metrics.
9. Generate a same-camera hand+laptop panel and require human ACCEPT/REJECT.
10. Export the deterministic F0 lineage/metric packet and terminal note; do not add Gate D1 as a VLM jury.

## Failure policy

Any missing owner, wrong variable spelling, unexpected shape, copied tensor, changed frozen hash, swallowed completion signal, failed rollback, or source/import mismatch is a hold. Never recover by selecting a pre-H0 hand, alternate H1 checkpoint, Gate-A initial object pose, or rejected O0 state.
