# O0 rigid laptop ownership and implementation plan

## Accepted upstream state

- Accepted H1 checkpoint: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_fixed_registration_five_attempt_v99_11_7_13_3_13_5_5_1_7_3_5_14_93_2/runtime/controller/checkpoints/H1_attempt_005.pt`
- SHA256: `f21a0ac081d6eb282f9d77e610faa99367f7d6174c1ca3a1d8399f956d482f4b`
- Gate-A laptop: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_c_clean_HOI_carrier_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14/runtime_import_and_guard_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_1/candidate_0_guarded_input_v99_11_7_13_3_13_5_5_1_7_3_5_14_2/clean_carrier_generation_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_3/clean_carrier_generation_execution_v99_11_7_13_3_13_5_5_1_7_3_5_14_4/actual_filename_adjudication_v99_11_7_13_3_13_5_5_1_7_3_5_14_5/carrier_to_MoGe_registration_v99_11_7_13_3_13_5_5_1_7_3_5_14_6/JSON_container_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_7/bounded_lineage_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_8/exact_field_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_9/RGBA_to_MoGe_RGB_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_10/matching_MoGe_execution_v99_11_7_13_3_13_5_5_1_7_3_5_14_11/exact_mask_carrier_support_v99_11_7_13_3_13_5_5_1_7_3_5_14_13/selected_camera_reprojection_v99_11_7_13_3_13_5_5_1_7_3_5_14_14/high_confidence_GateA_to_I_prepare_v99_11_7_13_3_13_5_5_1_7_3_5_14_15/object_target_acceptance_and_staged_route_v99_11_7_13_3_13_5_5_1_7_3_5_14_16/camera_aware_fitter_source_v99_11_7_13_3_13_5_5_1_7_3_5_14_17/bounded_CPU_candidates_v99_11_7_13_3_13_5_5_1_7_3_5_14_18/data/seed_2026_GateA_in_I.ply`
- SHA256: `a5fce8a985fca2226ef061f4c134c70c03332176a6fb7d7179c58bd23eccfce6`
- r04 face owner: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_r04_and_H0_H1_phase_contract_v99_11_7_13_3_13_5_5_1_7_3_5_14_65/config/GateA_r04_object_patch_map_v99_11_7_13_3_13_5_5_1_7_3_5_14_65.json`
- SHA256: `54bc9a57e186896f2ebf43dce6d44cdd03105f5d100eac96a8b885dec54573da`

## Ownership

- Exact trainable order: `global_object_rotation`, then `global_object_translation`.
- Live owners: `rotation_obj` and `trans_obj`.
- Frozen: accepted corrected-H1 hand, object scale/geometry/topology, camera, and observations.
- The accepted H1 hand is reconstructed through MANO -> Hshape -> `T_h2m` once -> accepted H0 scale/R/t -> accepted H1 residual, then detached and frozen.

## Dynamic evidence

- Every loss call rebuilds the object mesh from current R/t, rasterizes current metric depth and face IDs, derives current r04 pixels, and recomputes contact, z-order, collision, and observation losses.
- Every tentative update is rerendered before gate acceptance.  A rejected step restores values, trainability flags, optimizer state, gate state, and frozen hashes.

## Execution contract

- `backward-only`: zero updates; exact R/t gradients must be finite and nonzero.
- `capture-only`: zero gradients, zero updates, zero checkpoints, and exact state immutability.
- `optimize`: at most five attempts, one checkpoint per accepted attempt, no legacy object step when handled.
- O0 starts only after a zero-update live mesh/topology identity proof against Gate-A.

## Final policy

- There is no executable D1 VLM jury and no executable F0 optimizer.
- J0 completion performs a deterministic zero-update final audit/export; the human owns final ACCEPT/REJECT.

## Important project files

- Active pipeline deployment: `/home/fredcui/Projects/FollowMyHold/third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py`
- Tracked pipeline patch: `/home/fredcui/Projects/FollowMyHold/third_party_patches/hy3dgen/shapegen/pipelines.py`
- Production caller: `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/run.py`
- O0 runtime: `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/o0_transactional_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3.py`
- O0 binder: `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/o0_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3.py`
- O0 case manifest: `/home/fredcui/Projects/FollowMyHold/config/optimization/alapuse02v3n60_O0_case_manifest_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3.json`
- O0 policy: `/home/fredcui/Projects/FollowMyHold/config/optimization/O0_global_rigid_object_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3.json`
- O0 launcher: `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/run_alapuse02v3n60_d0_o0_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3.py`
- O0 integration test: `/home/fredcui/Projects/FollowMyHold/tests/hoiso_d0_objective_contract/test_O0_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3.py`
