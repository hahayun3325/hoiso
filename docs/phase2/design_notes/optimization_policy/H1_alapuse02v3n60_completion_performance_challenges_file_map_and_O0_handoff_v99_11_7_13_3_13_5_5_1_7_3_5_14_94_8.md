# H1 alapuse02v3n60 completion, performance, challenges, file map, and O0 handoff — 14_94_8

## Status

- Case: `alapuse02v3n60_auto_v2`.
- Phase: corrected H1 selected index/middle MANO articulation.
- Result: **technical PASS and human ACCEPT** for one bounded five-update diagnostic.
- Scope: this closes H1 for the staged pipeline; it is not a convergence or ground-truth certificate.
- Accepted terminal state: attempt 5.  Attempt 4 is retained as the lowest scalar-loss reference.

## What H1 changed

H0 fixed global hand rotation and translation.  H1 froze that accepted global placement, hand scale,
MANO root/shape/nonselected pose rows, object, camera, and observations.  It optimized only
`selected_so3_residual[6,3]` in ordered index MCP/PIP/DIP and middle MCP/PIP/DIP rows.

## Numeric result

| metric | initial | terminal | delta |
|---|---:|---:|---:|
| `loss_total` | 21.04698944091797 | 21.036945343017578 | -0.010044097900390625 |
| `loss_base` | 20.99244499206543 | 20.982219696044922 | -0.010225296020507812 |
| `loss_contact_xy` | 0.04442150890827179 | 0.04516018554568291 | 0.0007386766374111176 |
| `loss_contact_z` | 0.02658434957265854 | 0.025792986154556274 | -0.0007913634181022644 |
| `loss_zorder` | 0.009441359899938107 | 0.009603735990822315 | 0.00016237609088420868 |
| `loss_pose_prior` | 0.0 | 2.33041155297542e-05 | 2.33041155297542e-05 |
| `loss_joint_limit` | 0.0 | 0.0 | 0.0 |
| `loss_collision` | 0.06672602891921997 | 0.06738962978124619 | 0.0006636008620262146 |
| `loss_integrity` | 0.0 | 4.846704149130687e-10 | 4.846704149130687e-10 |

- Attempts/updates: `5` / `5`; rollback: `False`.
- Best scalar attempt: `4` at total loss `21.036643981933594`.
- Accepted terminal total loss: `21.036945343017578`.
- Peak allocated GPU bytes: `9862030692` (~9.18 GiB).
- Final selected residual norm: `0.020481064915657043`.

The terminal loss is below the initial loss, but attempt 5 is slightly above attempt 4.  The gate is
therefore bounded/permissive rather than strictly monotonic.  The user accepted the attempt-5 visual
state; no code should silently replace it with attempt 4.

## Visual result

- Final panel: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_fixed_registration_final_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_7/artifacts/alapuse02v3n60_corrected_H1_final_hand_laptop_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_7.png`
- Panel SHA256: `dd6ab1d63e1cc22d2ae12d5d5fb315ee7a3136da4ef6f92537ff87556e4681c4`
- Initial/final/laptop pixels: `2195` / `2186` / `22375`.
- The initial green and final magenta hands share the corrected H0 frame and production camera.
- The change is subtle and local to selected articulation; the cyan Gate-A laptop remains fixed.

## Challenges and resolutions

1. The original live hand owner was a fixed mesh, not an independently optimizable MANO articulation leaf.
2. The exact HaMeR carrier row, handedness, MANO asset, 15-pose order, root separation, and six selected rows had to be receipt-bound.
3. A differentiable local-MANO-to-Hshape bridge and CPU Jacobian proved all 18 selected coordinates while excluding forbidden owners.
4. H1 needed a transactional provider, binder, launcher, rollback/checkpoint runtime, and explicit production callback ownership.
5. Active runtime deployment and hidden-CUDA child environments had to be audited independently of shell transport success.
6. The first H1 run and panel omitted/misowned the fixed `T_h2m` registration and were correctly preserved as rejected evidence.
7. The repaired zero-update identity panel proved the real H0-to-H1 handoff before a fresh one-time H1 run was authorized.
8. Backward-only, capture-only, immutable unlock, one-time claim, five updates, metric audit, and read-only final panel all closed.
9. Optional legacy debug-export paths still print nonfatal missing-file messages; these are diagnostic debt, not missing H1 inputs.

## Important project files

- `third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py` — SHA256 `fa8d17be7c47016647a2a7466a7102da6e93aaa072cbc799aa3800ea8256d1b0`
- `third_party_patches/hy3dgen/shapegen/pipelines.py` — SHA256 `17ebc045e2e68752cd244201486a65757220bb29caeac3a9fa9c9c3f60f52fdb`
- `src/foho/guidance/h1_selected_finger_mano_provider_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_4.py` — SHA256 `b87cf43dfb3b66e66f6ea6dd5b230352a99705480fba7106bd05180c33343f60`
- `src/foho/guidance/h1_transactional_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_5.py` — SHA256 `47f80549557cd68725ebb0f6a16c33ea17c4a042e4a48772fc97f3d1002cccff`
- `src/foho/guidance/h1_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_5.py` — SHA256 `125c1db6eb47de3235205f76d07ed0a10686386459bb39f51acb2073e15f8a3e`
- `src/foho/guidance/run_alapuse02v3n60_d0_h1_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_5.py` — SHA256 `5a6002d2713dd332428cabcd2cd03e7f3044c28d2747c52dacecaf4c66f71d52`
- `config/optimization/H1_global_dimensionless_loss_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_5.json` — SHA256 `cef6a220eeb519843531e84c1bc84eb3aa19fac89df2f16db69fea19ef493aec`
- `src/foho/guidance/h1_read_only_registration_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_2.py` — SHA256 `deceb01a3d1e40b80a4559e24c01fc39a67b077222d21c161bb2162b0e6024bc`
- `src/foho/guidance/run_alapuse02v3n60_h1_registration_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_2.py` — SHA256 `ea7a66f058b7f83a91f55df7ebff5fc92ae5aac79fafa5acba35199e1197c54f`
- `tests/hoiso_d0_objective_contract/test_H1_selected_finger_mano_provider_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_4.py` — SHA256 `7e7868955bc8271dd02fb76acb4db2510cb050e81977ab621bd2308a961a8030`
- `tests/hoiso_d0_objective_contract/test_H1_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_5.py` — SHA256 `001fe10534c7f391a78da3f26135def697363ae75eecec6c749c302e69a3ad30`
- `tests/hoiso_d0_objective_contract/test_H1_read_only_registration_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_2.py` — SHA256 `1abb1dfd9095616f194c73247d248339b14f978b9b994b37b6a4cd8cd97c07d5`
- `tests/hoiso_d0_objective_contract/test_H1_fixed_registration_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_4_2.py` — SHA256 `0d61e8dc9d1772551aaca65e72c7c0e5cbf05c64dbdc183bb974e365f0a5035e`
- `tests/hoiso_d0_objective_contract/test_H1_panel_T_h2m_owner_forwarding_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_4_5.py` — SHA256 `8cf22f7897a7ba1bb3073b9122762cffdfe01d3996180ec10098f3c55e93fd6b`
- `docs/phase2/design_notes/optimization_policy/H1_selected_finger_MANO_articulation_implementation_plan_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_1.md` — SHA256 `77178be47f5fc3d7ef58cd7850369e77002ae3ea427a5739aece5e607e9337a8`
- `docs/phase2/design_notes/optimization_policy/H1_MANO_articulation_ownership_contract_and_file_map_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_2.md` — SHA256 `d06810b53250ad528d042ed107221ccb8ac0d717a1cec1e6e0aca64851f220e2`
- `third_party/estimator/hamer/_DATA/data/mano/MANO_RIGHT.pkl` — SHA256 `45d60aa3b27ef9107a7afd4e00808f307fd91111e1cfa35afd5c4a62de264767`

## Important accepted hand, object, receipt, and panel assets

- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_c_clean_HOI_carrier_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14/runtime_import_and_guard_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_1/candidate_0_guarded_input_v99_11_7_13_3_13_5_5_1_7_3_5_14_2/clean_carrier_generation_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_3/clean_carrier_generation_execution_v99_11_7_13_3_13_5_5_1_7_3_5_14_4/actual_filename_adjudication_v99_11_7_13_3_13_5_5_1_7_3_5_14_5/carrier_to_MoGe_registration_v99_11_7_13_3_13_5_5_1_7_3_5_14_6/JSON_container_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_7/bounded_lineage_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_8/exact_field_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_9/RGBA_to_MoGe_RGB_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_10/matching_MoGe_execution_v99_11_7_13_3_13_5_5_1_7_3_5_14_11/exact_mask_carrier_support_v99_11_7_13_3_13_5_5_1_7_3_5_14_13/selected_camera_reprojection_v99_11_7_13_3_13_5_5_1_7_3_5_14_14/high_confidence_GateA_to_I_prepare_v99_11_7_13_3_13_5_5_1_7_3_5_14_15/object_target_acceptance_and_staged_route_v99_11_7_13_3_13_5_5_1_7_3_5_14_16/camera_aware_fitter_source_v99_11_7_13_3_13_5_5_1_7_3_5_14_17/bounded_CPU_candidates_v99_11_7_13_3_13_5_5_1_7_3_5_14_18/selected_seed_and_fresh_hand_zero_step_v99_11_7_13_3_13_5_5_1_7_3_5_14_19/official_hand_chain_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_20/frame_archive_independent_hand_shape_v99_11_7_13_3_13_5_5_1_7_3_5_14_21/official_upper_hand_source_selection_v99_11_7_13_3_13_5_5_1_7_3_5_14_22/fresh_upper_only_HaMeR_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_23/generated/alapuse02v3n60upperL_0.npy` — SHA256 `e51ba66efbf28963f07cfd1991a5e34777e245803bb5d4e8a56a490cf80ef7f4`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_c_hand_constraint_first_CPU_v99_11_7_13_3_13_5_5_1_7_3_5_14_38/candidates/depth_median_CF_T_Hshape_to_I.npy` — SHA256 `0a8d117deb09c8fa002cdd1d4e840534f1b8e349da033eab75421beed15972c1`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_corrected_five_update_v99_11_7_13_3_13_5_5_1_7_3_5_14_88_7_1/runtime/controller/checkpoints/H0_step_005.pt` — SHA256 `8e382d5f712e520970e558d3c8cedf158d65e2281afc6ed99e4fd02cac926eb6`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_fixed_registration_five_attempt_v99_11_7_13_3_13_5_5_1_7_3_5_14_93_2/runtime/controller/checkpoints/H1_attempt_005.pt` — SHA256 `f21a0ac081d6eb282f9d77e610faa99367f7d6174c1ca3a1d8399f956d482f4b`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_fixed_registration_five_attempt_v99_11_7_13_3_13_5_5_1_7_3_5_14_93_2/runtime/controller/checkpoints/H1_attempt_004.pt` — SHA256 `a8194cb66dfd1dca05c31a18cc856b9ba762e4a762de9fbd511a45b4ac16afce`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_c_clean_HOI_carrier_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14/runtime_import_and_guard_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_1/candidate_0_guarded_input_v99_11_7_13_3_13_5_5_1_7_3_5_14_2/clean_carrier_generation_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_3/clean_carrier_generation_execution_v99_11_7_13_3_13_5_5_1_7_3_5_14_4/actual_filename_adjudication_v99_11_7_13_3_13_5_5_1_7_3_5_14_5/carrier_to_MoGe_registration_v99_11_7_13_3_13_5_5_1_7_3_5_14_6/JSON_container_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_7/bounded_lineage_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_8/exact_field_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_9/RGBA_to_MoGe_RGB_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_10/matching_MoGe_execution_v99_11_7_13_3_13_5_5_1_7_3_5_14_11/exact_mask_carrier_support_v99_11_7_13_3_13_5_5_1_7_3_5_14_13/selected_camera_reprojection_v99_11_7_13_3_13_5_5_1_7_3_5_14_14/high_confidence_GateA_to_I_prepare_v99_11_7_13_3_13_5_5_1_7_3_5_14_15/object_target_acceptance_and_staged_route_v99_11_7_13_3_13_5_5_1_7_3_5_14_16/camera_aware_fitter_source_v99_11_7_13_3_13_5_5_1_7_3_5_14_17/bounded_CPU_candidates_v99_11_7_13_3_13_5_5_1_7_3_5_14_18/data/seed_2026_GateA_in_I.ply` — SHA256 `a5fce8a985fca2226ef061f4c134c70c03332176a6fb7d7179c58bd23eccfce6`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_outer_caller_and_mesh_contract_repair_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_9/reports/exact_frozen_GateA_mesh_owner_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_9.json` — SHA256 `c70ca8f5af61a9ea0deccc9f9d88992448072b0b8af165858f8e98386e78e17e`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_r04_and_H0_H1_phase_contract_v99_11_7_13_3_13_5_5_1_7_3_5_14_65/config/GateA_r04_object_patch_map_v99_11_7_13_3_13_5_5_1_7_3_5_14_65.json` — SHA256 `54bc9a57e186896f2ebf43dce6d44cdd03105f5d100eac96a8b885dec54573da`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_optional_RGB_and_dense_patch_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_63/data/GateA_dense_depth_face_ids_v99_11_7_13_3_13_5_5_1_7_3_5_14_63.npz` — SHA256 `d74b455456ffb60253017592c11804a3904f207c49e1630acc50f457a7680269`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_metric_rim_expansion_v99_11_7_13_3_13_5_5_1_7_3_5_14_64/data/three_metric_connected_rim_expansions_v99_11_7_13_3_13_5_5_1_7_3_5_14_64.npz` — SHA256 `ca73e2c10c84cce37a78a16697575fa1b26110d1944cd17d87d660031300181d`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_corrected_final_evaluation_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_10_5/artifacts/alapuse02v3n60_corrected_H0_final_hand_laptop_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_10_5.png` — SHA256 `fad6c375f6ea63ecbb8151485ed3f6c0d7755066734609aab31300f71fb825ab`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_fixed_registration_identity_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_4_7/artifacts/alapuse02v3n60_H1_fixed_registration_identity_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_4_7.png` — SHA256 `a6815863163c8ad718ffd78f538fc11504a38b61bc37915fd33147a5bc29d8b7`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_fixed_registration_final_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_7/artifacts/alapuse02v3n60_corrected_H1_final_hand_laptop_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_7.png` — SHA256 `dd6ab1d63e1cc22d2ae12d5d5fb315ee7a3136da4ef6f92537ff87556e4681c4`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_fixed_registration_five_attempt_v99_11_7_13_3_13_5_5_1_7_3_5_14_93_2/reports/H1_five_attempt_audit_v99_11_7_13_3_13_5_5_1_7_3_5_14_93_2.json` — SHA256 `c54e2cb136ac04842dec77d67b026caa4ec155423e3956c0332e31e2a37c0ae1`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_fixed_registration_evaluation_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_6/reports/H1_trajectory_and_metric_delta_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_6.json` — SHA256 `a8d3a65a5444739eaba673a415d1b4d509ffdb1e34922e525cd1a44cea6e20dd`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_fixed_registration_final_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_7/reports/H1_final_panel_audit_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_7.json` — SHA256 `6f0c47004b0f2b53d95fbf6ccef6c1aef7102dd37c15b7b0cd8ccb0a02d1b96f`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_fixed_registration_final_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_7/reports/H1_final_panel_human_ACCEPT_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_7.json` — SHA256 `e10c4bd009865ba77995b86d55ecf86f49b25e3cfc4060318cc814f416e4248d`

## O0 handoff

- Freeze the human-accepted H1 attempt-5 hand, its H0 global R/t, camera, and observations.
- Treat `seed_2026_GateA_in_I.ply` as the authoritative starting laptop, not the Hunyuan HOI or MoGe meshes.
- Prove exact live object pose/articulation tensor identity and order before adding an optimizer.
- Recompute moving object vertices, raster, metric depth, face visibility, and r04 support on every tentative O0 update and post-update gate.
- Run O0 backward-only, capture-only, one bounded optimize, numeric audit, same-camera panel, and human review before J0.
- O0 remains unauthorized at the time this note is written.
