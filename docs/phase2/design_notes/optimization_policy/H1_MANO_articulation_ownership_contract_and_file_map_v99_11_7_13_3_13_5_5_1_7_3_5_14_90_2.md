# H1 MANO articulation ownership contract and file map

## Status

H0 is closed and accepted.  H1 is locked (`authorized=0`, `spent=0`,
`executable=false`).  The active production path currently owns only a fixed
MANO-topology mesh; no differentiable parametric MANO articulation owner is
installed at the H1 seam.

## Why this contract exists

“The hand” has several distinct owners.  Confusing them would make a test pass
while optimizing the wrong object:

1. **Parameter-carrier owner:** the receipt-owned HaMeR artifact containing
   base hand pose, global orientation, shape/betas, handedness, and representation.
2. **Model owner:** exact MANO implementation and model assets that turn those
   parameters into the ordered 778 vertices and 1552 faces.
3. **Trainable owner:** a new selected index/middle residual leaf.  It is the
   only H1 optimizer parameter.
4. **Geometry owner:** the MANO vertices generated from the composed pose.
   Generated vertices are not themselves optimizer leaves.
5. **Frame owner:** upper-left HaMeR space -> recovered immediate Hshape ->
   accepted CPU transform -> accepted H0 global R/T -> renderer camera.
6. **Selection owner:** D0/finger map plus the exact MANO joint/axis convention
   and selected pad vertices.

## Accepted evidence and important paths

- active pipeline: `/home/fredcui/Projects/FollowMyHold/third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py`
- scope-aware source packet: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_final_accept_and_H1_plan_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_1/reports/H1_exact_live_MANO_source_packet_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_1.json`
- mesh-only gap receipt: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_parametric_owner_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_2/reports/H1_mesh_only_owner_gap_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_2.json`
- corrected hand triplet: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_intermediate_Hshape_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_10_2/config/corrected_H0_hand_source_triplet_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_10_2.json`
- corrected call packet: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_intermediate_Hshape_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_10_2/config/alapuse02v3n60_corrected_H0_call_arguments_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_10_2.json`
- receipt-owned guidance carrier: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_c_clean_HOI_carrier_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14/runtime_import_and_guard_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_1/candidate_0_guarded_input_v99_11_7_13_3_13_5_5_1_7_3_5_14_2/clean_carrier_generation_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_3/clean_carrier_generation_execution_v99_11_7_13_3_13_5_5_1_7_3_5_14_4/actual_filename_adjudication_v99_11_7_13_3_13_5_5_1_7_3_5_14_5/carrier_to_MoGe_registration_v99_11_7_13_3_13_5_5_1_7_3_5_14_6/JSON_container_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_7/bounded_lineage_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_8/exact_field_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_9/RGBA_to_MoGe_RGB_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_10/matching_MoGe_execution_v99_11_7_13_3_13_5_5_1_7_3_5_14_11/exact_mask_carrier_support_v99_11_7_13_3_13_5_5_1_7_3_5_14_13/selected_camera_reprojection_v99_11_7_13_3_13_5_5_1_7_3_5_14_14/high_confidence_GateA_to_I_prepare_v99_11_7_13_3_13_5_5_1_7_3_5_14_15/object_target_acceptance_and_staged_route_v99_11_7_13_3_13_5_5_1_7_3_5_14_16/camera_aware_fitter_source_v99_11_7_13_3_13_5_5_1_7_3_5_14_17/bounded_CPU_candidates_v99_11_7_13_3_13_5_5_1_7_3_5_14_18/selected_seed_and_fresh_hand_zero_step_v99_11_7_13_3_13_5_5_1_7_3_5_14_19/official_hand_chain_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_20/frame_archive_independent_hand_shape_v99_11_7_13_3_13_5_5_1_7_3_5_14_21/official_upper_hand_source_selection_v99_11_7_13_3_13_5_5_1_7_3_5_14_22/fresh_upper_only_HaMeR_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_23/generated/alapuse02v3n60upperL_kps_for_guidance.npy`
- recovered fixed mesh supplied to H0: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_intermediate_Hshape_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_10_2/artifacts/alapuse02v3n60_recovered_immediate_Hshape_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_10_2.ply`
- accepted Hshape-to-I transform: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_c_hand_constraint_first_CPU_v99_11_7_13_3_13_5_5_1_7_3_5_14_38/candidates/depth_median_CF_T_Hshape_to_I.npy`
- accepted H0 checkpoint: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_corrected_five_update_v99_11_7_13_3_13_5_5_1_7_3_5_14_88_7_1/runtime/controller/checkpoints/H0_step_005.pt`
- H0 binder: `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/h0_manifest_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_9.py`
- H0 launcher: `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/run_alapuse02v3n60_d0_h0_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_2.py`
- H1 implementation proposal: `/home/fredcui/Projects/FollowMyHold/docs/phase2/design_notes/optimization_policy/H1_selected_finger_MANO_articulation_implementation_plan_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_1.md`
- this ownership contract: `/home/fredcui/Projects/FollowMyHold/docs/phase2/design_notes/optimization_policy/H1_MANO_articulation_ownership_contract_and_file_map_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_2.md`

## Evidence already closed

- The active source loads `mano_verts` from `aligned_mano_mesh_path`.
- `mano_mesh_moge` is treated as frozen during H0.
- `FINGERTIP_IDXS_MANO`, `mano_to_openpose`, and `J_regressor` compute
  measurements from vertices; they do not expose articulation coefficients.
- The legacy `joint_optimizer` is not evidence of MANO pose ownership.

## Required proof before production H1 binding

The selected parameter carrier and MANO model must regenerate the exact
receipt-owned upper-left raw mesh with ordered topology and a bounded maximum
vertex error.  The contract must then record:

- handedness and MANO model identity/hash;
- pose representation (axis-angle, rotation matrices, PCA, or other), shape,
  joint ordering, units, and composition rule;
- immutable base pose/shape/global orientation hashes;
- ordered index/middle joint and tangent-axis allowlist;
- selected-pad Jacobian finite/nonzero and forbidden-dimension exclusion;
- full registration chain into the H0/render frame;
- exact frozen ledger for accepted global R/T, scale, root, shape,
  nonselected joints, laptop, camera, and observations.

## Forbidden shortcuts

- Do not optimize `mano_verts` directly.
- Do not infer joint indices from OpenPose ordering.
- Do not add matrix entries when the carrier stores rotation matrices; compose
  a valid tangent rotation.
- Do not use the generic legacy `joint_optimizer` as proof of H1 ownership.
- Do not refit or rerun HaMeR without proving reproduction of the accepted
  raw upper-left hand and preserving its receipt lineage.

## Planned source targets after provider proof

- `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/h1_mano_parameter_provider_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_3.py`
- `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/h1_selected_finger_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_3.py`
- `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/run_alapuse02v3n60_d0_h1_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_3.py`
- `/home/fredcui/Projects/FollowMyHold/config/optimization/H1_selected_finger_dimensionless_loss_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_3.json`
- `/home/fredcui/Projects/FollowMyHold/tests/hoiso_d0_objective_contract/test_H1_MANO_owner_and_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_3.py`

Production source remains unchanged until these owner predicates pass.
