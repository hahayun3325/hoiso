# O0 completion, performance, challenges, file map, and J0 handoff

## Status

Case `alapuse02v3n60` completed O0 with five attempted and five accepted updates. The terminal object state is `O0_attempt_005.pt`. Corrected H1 is frozen. Human O0 review is **ACCEPT**. O0 is spent and non-executable.

## Performance and visual result

The terminal same-camera panel preserves the coherent laptop topology and scale. Initial and final laptop support are 22,375 and 22,353 pixels. Their contours largely overlap, consistent with a small rigid correction. Final r04 support is nonempty at 166 pixels. Total loss ends slightly below its initial value (approximately 1571.4 to 1569.77), although the five-attempt path is non-monotonic. The accepted H1 hand remains unchanged.

Human note: Laptop shape and scale remain coherent; the final magenta pose is a small rigid change from cyan, the accepted H1 hand stays fixed, and no visible frame or topology regression is present.

## Challenges closed

1. Production child-environment and module-owner collisions were separated from scientific failures.
2. The O0 callback was bound at the actual live Phase-1.5 seam.
3. Accepted H1 hand identity and the Gate-A object mesh owner were hash pinned.
4. O0 was limited to rigid object R/t while hand, topology, camera, and semantic ownership remained frozen.
5. Backward-only and capture-only proved gradients and zero updates before spending the five-attempt reservation.
6. The read-only panel initially lacked the canonical live object owner; the binder-before-read repair closed it.
7. A raw source-word validator mistook the receipt key `optimizer_updates` for optimizer behavior; an AST call-level validator replaced it.
8. The panel replay was proven read-only and checkpoint preserving.

## Authoritative artifacts

- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_fixed_registration_five_attempt_v99_11_7_13_3_13_5_5_1_7_3_5_14_93_2/runtime/controller/checkpoints/H1_attempt_005.pt`
  SHA256: `f21a0ac081d6eb282f9d77e610faa99367f7d6174c1ca3a1d8399f956d482f4b`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_fixed_registration_final_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_7/reports/H1_final_panel_human_ACCEPT_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_7.json`
  SHA256: `e10c4bd009865ba77995b86d55ecf86f49b25e3cfc4060318cc814f416e4248d`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_O0_five_attempt_v99_11_7_13_3_13_5_5_1_7_3_5_14_98/reports/O0_optimize_raw_v99_11_7_13_3_13_5_5_1_7_3_5_14_98.json`
  SHA256: `c6c7742b0e71767b6e7b2f11db5bab2537e17cd5c2e04f7346d9a62a151d8c22`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_O0_five_attempt_v99_11_7_13_3_13_5_5_1_7_3_5_14_98/runtime/controller/checkpoints/O0_attempt_005.pt`
  SHA256: `b6a5adf128be9a3bec622bc5d23c590942d7b137984f5879d75f2aed9ed86a64`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_O0_evaluation_v99_11_7_13_3_13_5_5_1_7_3_5_14_99/reports/O0_five_attempt_execution_audit_v99_11_7_13_3_13_5_5_1_7_3_5_14_99.json`
  SHA256: `b45cce3d7eef1b14c2432dfbe77b1b1622da90e153f51d8d65126efaa2dace02`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_O0_evaluation_v99_11_7_13_3_13_5_5_1_7_3_5_14_99/reports/O0_trajectory_and_metric_delta_v99_11_7_13_3_13_5_5_1_7_3_5_14_99.json`
  SHA256: `beec67bc6227b32d8219606189cd5c11cb2b37d3625e17f5854e55b0d5ad824d`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_O0_same_camera_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_99_2_5/panels/alapuse02v3n60_O0_same_camera_fixed_H1_hand_initial_final_laptop_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_99_2_5.png`
  SHA256: `ad2551e1798cea8b795ff0aab106ff2e7fa237beb7a999517276be95402d34da`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_O0_same_camera_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_99_2_5/reports/O0_panel_and_immutability_v99_11_7_13_3_13_5_5_1_7_3_5_14_99_2_5.json`
  SHA256: `27b5334672d3c7e2a1418fa6c00b509fbd48980ffeb49f98ff6253371f5a704c`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_O0_panel_validator_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_99_2_3_1/reports/O0_panel_validator_commit_push_v99_11_7_13_3_13_5_5_1_7_3_5_14_99_2_3_1.json`
  SHA256: `b298d41fd2f2ac3ea6708e3137e85697b0107d393041a4f337c0b5e79e935d41`

## Production sources and contracts

- `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/o0_transactional_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3.py`
  SHA256: `f7e5e19a393d69d3a677adb4707b6f38f3541c3bad227a931e3564090a19a773`
- `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/o0_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3.py`
  SHA256: `89556a8dfb9642e3f7c87c8669d2bbf0eb7b54e68a545c5d7fb5b1ecbc1a72d2`
- `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/run_alapuse02v3n60_d0_o0_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3.py`
  SHA256: `79220c02f70f03139eeb0a0e8c763a891be02ad9e1bd7c11e2f493a52b17a918`
- `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/o0_read_only_same_camera_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_99_1.py`
  SHA256: `bec491b94e1561b0985b110899c0f583629240df9ee4cb483f354f69090c013f`
- `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/run_alapuse02v3n60_o0_same_camera_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_99_1.py`
  SHA256: `c0c395822aa59d69bfaa40f433ccc88c37ea10d139c0fcff414245e70687f6bf`
- `/home/fredcui/Projects/FollowMyHold/config/optimization/alapuse02v3n60_O0_case_manifest_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3.json`
  SHA256: `8267df851e683add480f737cc6b91c0a3c2fb6c15126cb2b81a7b2496714b591`
- `/home/fredcui/Projects/FollowMyHold/config/optimization/O0_global_rigid_object_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3.json`
  SHA256: `a421b7023dd08ab23f169f7af5a7d30b055d58a8aab3247f6efbecf6a499a21c`
- `/home/fredcui/Projects/FollowMyHold/third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py`
  SHA256: `0eabad456a90763e1d940424ed9dc966738cf00c0989276de10e6889de5fa05d`

## Extended authoritative asset map

The following paths are authoritative for reproducing O0 and initializing J0.  Historical provenance assets are documented but are not alternate runtime inputs.

- **Raw selected HaMeR hand carrier**
  - path: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_c_clean_HOI_carrier_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14/runtime_import_and_guard_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_1/candidate_0_guarded_input_v99_11_7_13_3_13_5_5_1_7_3_5_14_2/clean_carrier_generation_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_3/clean_carrier_generation_execution_v99_11_7_13_3_13_5_5_1_7_3_5_14_4/actual_filename_adjudication_v99_11_7_13_3_13_5_5_1_7_3_5_14_5/carrier_to_MoGe_registration_v99_11_7_13_3_13_5_5_1_7_3_5_14_6/JSON_container_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_7/bounded_lineage_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_8/exact_field_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_9/RGBA_to_MoGe_RGB_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_10/matching_MoGe_execution_v99_11_7_13_3_13_5_5_1_7_3_5_14_11/exact_mask_carrier_support_v99_11_7_13_3_13_5_5_1_7_3_5_14_13/selected_camera_reprojection_v99_11_7_13_3_13_5_5_1_7_3_5_14_14/high_confidence_GateA_to_I_prepare_v99_11_7_13_3_13_5_5_1_7_3_5_14_15/object_target_acceptance_and_staged_route_v99_11_7_13_3_13_5_5_1_7_3_5_14_16/camera_aware_fitter_source_v99_11_7_13_3_13_5_5_1_7_3_5_14_17/bounded_CPU_candidates_v99_11_7_13_3_13_5_5_1_7_3_5_14_18/selected_seed_and_fresh_hand_zero_step_v99_11_7_13_3_13_5_5_1_7_3_5_14_19/official_hand_chain_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_20/frame_archive_independent_hand_shape_v99_11_7_13_3_13_5_5_1_7_3_5_14_21/official_upper_hand_source_selection_v99_11_7_13_3_13_5_5_1_7_3_5_14_22/fresh_upper_only_HaMeR_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_23/generated/alapuse02v3n60upperL_0.npy`
  - SHA256: `e51ba66efbf28963f07cfd1991a5e34777e245803bb5d4e8a56a490cf80ef7f4`
  - role: historical provenance only; never reload directly in J0
- **MANO model asset**
  - path: `/home/fredcui/Projects/FollowMyHold/third_party/estimator/hamer/_DATA/data/mano/MANO_RIGHT.pkl`
  - SHA256: `45d60aa3b27ef9107a7afd4e00808f307fd91111e1cfa35afd5c4a62de264767`
  - role: parametric hand provider asset
- **Hand-to-MoGe registration**
  - path: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_c_hand_constraint_first_CPU_v99_11_7_13_3_13_5_5_1_7_3_5_14_38/candidates/depth_median_CF_T_Hshape_to_I.npy`
  - SHA256: `0a8d117deb09c8fa002cdd1d4e840534f1b8e349da033eab75421beed15972c1`
  - role: historical frame transform used before accepted H0/H1
- **H1 local-to-Hshape bridge**
  - path: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_bridge_and_reusable_provider_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_4/config/alapuse02v3n60_local_MANO_to_Hshape_bridge_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_4.json`
  - SHA256: `0af8dd93abc5a3dfff439e8cd9bef3a002d4737232d22bd8c8600c7d27579e2b`
  - role: ordered differentiable hand bridge
- **H1 MANO residual provider**
  - path: `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/h1_selected_finger_mano_provider_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_4.py`
  - SHA256: `b87cf43dfb3b66e66f6ea6dd5b230352a99705480fba7106bd05180c33343f60`
  - role: selected-finger parametric owner
- **Accepted H1 checkpoint**
  - path: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_fixed_registration_five_attempt_v99_11_7_13_3_13_5_5_1_7_3_5_14_93_2/runtime/controller/checkpoints/H1_attempt_005.pt`
  - SHA256: `f21a0ac081d6eb282f9d77e610faa99367f7d6174c1ca3a1d8399f956d482f4b`
  - role: operative terminal hand owner
- **Accepted H1 panel**
  - path: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_fixed_registration_final_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_7/artifacts/alapuse02v3n60_corrected_H1_final_hand_laptop_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_7.png`
  - SHA256: `dd6ab1d63e1cc22d2ae12d5d5fb315ee7a3136da4ef6f92537ff87556e4681c4`
  - role: human-accepted hand visual evidence
- **Gate-A initial object mesh**
  - path: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_c_clean_HOI_carrier_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14/runtime_import_and_guard_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_1/candidate_0_guarded_input_v99_11_7_13_3_13_5_5_1_7_3_5_14_2/clean_carrier_generation_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_3/clean_carrier_generation_execution_v99_11_7_13_3_13_5_5_1_7_3_5_14_4/actual_filename_adjudication_v99_11_7_13_3_13_5_5_1_7_3_5_14_5/carrier_to_MoGe_registration_v99_11_7_13_3_13_5_5_1_7_3_5_14_6/JSON_container_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_7/bounded_lineage_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_8/exact_field_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_9/RGBA_to_MoGe_RGB_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_10/matching_MoGe_execution_v99_11_7_13_3_13_5_5_1_7_3_5_14_11/exact_mask_carrier_support_v99_11_7_13_3_13_5_5_1_7_3_5_14_13/selected_camera_reprojection_v99_11_7_13_3_13_5_5_1_7_3_5_14_14/high_confidence_GateA_to_I_prepare_v99_11_7_13_3_13_5_5_1_7_3_5_14_15/object_target_acceptance_and_staged_route_v99_11_7_13_3_13_5_5_1_7_3_5_14_16/camera_aware_fitter_source_v99_11_7_13_3_13_5_5_1_7_3_5_14_17/bounded_CPU_candidates_v99_11_7_13_3_13_5_5_1_7_3_5_14_18/data/seed_2026_GateA_in_I.ply`
  - SHA256: `a5fce8a985fca2226ef061f4c134c70c03332176a6fb7d7179c58bd23eccfce6`
  - role: historical object provenance; not J0 initial pose
- **r04 object patch map**
  - path: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_r04_and_H0_H1_phase_contract_v99_11_7_13_3_13_5_5_1_7_3_5_14_65/config/GateA_r04_object_patch_map_v99_11_7_13_3_13_5_5_1_7_3_5_14_65.json`
  - SHA256: `54bc9a57e186896f2ebf43dce6d44cdd03105f5d100eac96a8b885dec54573da`
  - role: object support/contact semantic owner
- **Accepted O0 checkpoint**
  - path: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_O0_five_attempt_v99_11_7_13_3_13_5_5_1_7_3_5_14_98/runtime/controller/checkpoints/O0_attempt_005.pt`
  - SHA256: `b6a5adf128be9a3bec622bc5d23c590942d7b137984f5879d75f2aed9ed86a64`
  - role: operative terminal object owner and primary J0 packet
- **O0 trajectory metrics**
  - path: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_O0_evaluation_v99_11_7_13_3_13_5_5_1_7_3_5_14_99/reports/O0_trajectory_and_metric_delta_v99_11_7_13_3_13_5_5_1_7_3_5_14_99.json`
  - SHA256: `beec67bc6227b32d8219606189cd5c11cb2b37d3625e17f5854e55b0d5ad824d`
  - role: numeric O0 evaluation
- **Accepted O0 panel**
  - path: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_O0_same_camera_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_99_2_5/panels/alapuse02v3n60_O0_same_camera_fixed_H1_hand_initial_final_laptop_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_99_2_5.png`
  - SHA256: `ad2551e1798cea8b795ff0aab106ff2e7fa237beb7a999517276be95402d34da`
  - role: human-accepted same-camera evidence
- **O0 runtime**
  - path: `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/o0_transactional_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3.py`
  - SHA256: `f7e5e19a393d69d3a677adb4707b6f38f3541c3bad227a931e3564090a19a773`
  - role: transactional object optimizer
- **O0 binder**
  - path: `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/o0_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3.py`
  - SHA256: `89556a8dfb9642e3f7c87c8669d2bbf0eb7b54e68a545c5d7fb5b1ecbc1a72d2`
  - role: accepted-H1/object binding owner
- **O0 launcher**
  - path: `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/run_alapuse02v3n60_d0_o0_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3.py`
  - SHA256: `79220c02f70f03139eeb0a0e8c763a891be02ad9e1bd7c11e2f493a52b17a918`
  - role: bounded execution entry point
- **O0 panel module**
  - path: `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/o0_read_only_same_camera_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_99_1.py`
  - SHA256: `bec491b94e1561b0985b110899c0f583629240df9ee4cb483f354f69090c013f`
  - role: read-only same-camera renderer
- **O0 panel launcher**
  - path: `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/run_alapuse02v3n60_o0_same_camera_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_99_1.py`
  - SHA256: `c0c395822aa59d69bfaa40f433ccc88c37ea10d139c0fcff414245e70687f6bf`
  - role: panel replay entry point
- **O0 case manifest**
  - path: `/home/fredcui/Projects/FollowMyHold/config/optimization/alapuse02v3n60_O0_case_manifest_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3.json`
  - SHA256: `8267df851e683add480f737cc6b91c0a3c2fb6c15126cb2b81a7b2496714b591`
  - role: case-specific frozen paths and hashes
- **O0 policy**
  - path: `/home/fredcui/Projects/FollowMyHold/config/optimization/O0_global_rigid_object_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3.json`
  - SHA256: `a421b7023dd08ab23f169f7af5a7d30b055d58a8aab3247f6efbecf6a499a21c`
  - role: bounded object-motion policy
- **Active production pipeline**
  - path: `/home/fredcui/Projects/FollowMyHold/third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py`
  - SHA256: `0eabad456a90763e1d940424ed9dc966738cf00c0989276de10e6889de5fa05d`
  - role: live callback seam owner

J0 must resolve the accepted hand through the O0 terminal lineage.  It must not substitute the raw HaMeR carrier, CPU-registered hand, Gate-A object pose, or another checkpoint.
## J0 handoff contract

J0 must begin from exactly the accepted corrected-H1 hand checkpoint and accepted O0 attempt-5 object checkpoint above. It must not reload the CPU-only hand, pre-H1 hand, Gate-A initial object pose, or any rejected H1/O0 checkpoint. J0 is a small trust-region joint residual phase: contact/image losses couple the two bodies, while deviation penalties keep the hand near accepted H1 and the object near accepted O0. Exact trainable residuals and the live callback owner must be proven before implementation. J0 optimization remains locked until CPU identity/Jacobian tests, backward-only, and capture-only pass.

## Final evaluation policy

D1 is not a mandatory VLM jury. After J0, F0 will export deterministic lineage, hashes, attempted/accepted updates, rollback state, losses, contact/r04/depth/z-order/collision evidence, and the final same-camera panel. The final semantic decision is explicit human ACCEPT or REJECT.
