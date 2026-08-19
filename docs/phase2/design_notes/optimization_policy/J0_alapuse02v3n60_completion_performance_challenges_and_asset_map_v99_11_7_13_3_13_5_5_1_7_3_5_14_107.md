# J0 completion, performance, challenges, and asset map: alapuse02v3n60

## Terminal decision

J0, F0, and human review are closed.  The canonical final alignment is
`/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_J0_evaluation_v99_11_7_13_3_13_5_5_1_7_3_5_14_104_3/checkpoints/J0_terminal_accepted_v99_11_7_13_3_13_5_5_1_7_3_5_14_104_3.pt` with SHA-256 `d062194c0a84a3acbc910eaf5d4a8c81027e3703217e3a1fe0613d17b5c7ee7a`.
No D1 jury and no additional optimizer run are authorized.

## Variable contract

The serialized trainable order is `global_hand_rotation`,
`global_hand_translation`, `global_object_rotation`, and
`global_object_translation`.  `selected_so3_residual` is carried as frozen
state and is exactly equal to the accepted H1 articulation.

## Performance

- total loss: `1590.7496337890625 -> 1588.7203369140625`;
- hand base: `20.982219696044922 -> 20.957508087158203`;
- object base: `1569.6788330078125 -> 1567.6844482421875`;
- contact XY: `0.05102870240807533 -> 0.04694893956184387`;
- contact Z: `0.02850440703332424 -> 0.022198636084794998`;
- collision: `0.09075087308883667 -> 0.08914997428655624`;
- hand motion: `0.07912936061620712 deg`, `0.7251554634422064 mm`;
- object motion: `0.06852804124355316 deg`, `0.4973636823706329 mm`;
- selected MANO residual L2 change: `0.0`;
- support count: `166 -> 171`; z-order remains zero with seven valid samples.

Attempt 4 has the lowest scalar total; attempt 5 is the policy-accepted terminal
checkpoint.  The trajectory is a successful bounded accept/rollback search,
not smooth monotonic convergence.

## Visual result

The same-camera panel is accepted.  The final hand remains in the observed
grasp region, the laptop shape is preserved, and contact is maintained at the
upper-left display edge.  Residual limitations are a compact/opaque hand
render and a non-pixel-perfect object mask; no frame or path mismatch remains.

## Challenges and technical debt

The difficult part was not the final joint step itself.  It was proving exact
owners across frame transforms, callback lifecycle, serialized schemas, and
panel reconstruction.  The replay still reports nonblocking debug-path
FileNotFound messages, one invalid-mesh diagnostic, and timm/autocast/torch.load
warnings.  It also reloads much of production merely to render.  A pure
terminal-checkpoint renderer is the preferred cleanup.  A cosmetically garbled
transcript line does not affect the final JSON receipts.

## Authoritative assets

- `H0 checkpoint`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_corrected_five_update_v99_11_7_13_3_13_5_5_1_7_3_5_14_88_7_1/runtime/controller/checkpoints/H0_step_005.pt`; SHA-256 `8e382d5f712e520970e558d3c8cedf158d65e2281afc6ed99e4fd02cac926eb6`
- `H1 checkpoint`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_fixed_registration_five_attempt_v99_11_7_13_3_13_5_5_1_7_3_5_14_93_2/runtime/controller/checkpoints/H1_attempt_005.pt`; SHA-256 `f21a0ac081d6eb282f9d77e610faa99367f7d6174c1ca3a1d8399f956d482f4b`
- `O0 checkpoint`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_O0_five_attempt_v99_11_7_13_3_13_5_5_1_7_3_5_14_98/runtime/controller/checkpoints/O0_attempt_005.pt`; SHA-256 `b6a5adf128be9a3bec622bc5d23c590942d7b137984f5879d75f2aed9ed86a64`
- `J0 terminal checkpoint`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_J0_evaluation_v99_11_7_13_3_13_5_5_1_7_3_5_14_104_3/checkpoints/J0_terminal_accepted_v99_11_7_13_3_13_5_5_1_7_3_5_14_104_3.pt`; SHA-256 `d062194c0a84a3acbc910eaf5d4a8c81027e3703217e3a1fe0613d17b5c7ee7a`
- `J0 trajectory JSON`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_J0_evaluation_v99_11_7_13_3_13_5_5_1_7_3_5_14_104_3/reports/J0_trajectory_and_metric_delta_v99_11_7_13_3_13_5_5_1_7_3_5_14_104_3.json`; SHA-256 `78854b5e8deaed0c58342372a8e7f57fe2b91cebc5d1b516b7b6fe509ef3a182`
- `J0 attempt CSV`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_J0_evaluation_v99_11_7_13_3_13_5_5_1_7_3_5_14_104_3/reports/J0_attempt_trajectory_v99_11_7_13_3_13_5_5_1_7_3_5_14_104_3.csv`; SHA-256 `9b1f921c6073450a4837f62abc3f3cb735f5192d6805b59d8092dbc1164318d2`
- `J0 manifest`: `/home/fredcui/Projects/FollowMyHold/config/optimization/alapuse02v3n60_J0_case_manifest_v99_11_7_13_3_13_5_5_1_7_3_5_14_100_2.json`; SHA-256 `acc3d0aa04232162161360074c1697ba850504731c50e4398505471257300912`
- `J0 binder`: `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/j0_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_100_2.py`; SHA-256 `6b68fa28281a4a2b003bb0875eb91cb0b279aac307b1509f2deb4343ec6a2aee`
- `guidance caller`: `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/run.py`; SHA-256 `4b0c454ac29ff4d30b120a9d3546fed6cecbef5b68efdc51eb63381e7d9ac090`
- `final J0 panel`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_J0_same_camera_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_105_5/panels/alapuse02v3n60_J0_same_camera_H1_O0_initial_final_joint_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_105_5.png`; SHA-256 `457f562ab001c73a5e6b6c92e4aff542444fcfe5108e39b75de89d33a0ec1733`
- `F0 receipt`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_J0_same_camera_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_105_5/reports/F0_internal_J0_validation_v99_11_7_13_3_13_5_5_1_7_3_5_14_105_5.json`; SHA-256 `7d92695a5fa9ee11fc3a90fcf58c3ffac99610382942038afe94375d924f1cc0`
- `human ACCEPT receipt`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_J0_final_closure_v99_11_7_13_3_13_5_5_1_7_3_5_14_107/receipts/human_J0_final_ACCEPT_v99_11_7_13_3_13_5_5_1_7_3_5_14_107.json`; SHA-256 `cda059040029d54e6d6178af88c73386e26b67632ee811e3f0402aa2fcf0b1d0`
- `evaluation contract`: `/home/fredcui/Projects/FollowMyHold/docs/phase2/design_notes/optimization_policy/alapuse02v3n60_evaluation_validation_and_paper_comparison_contract_v99_11_7_13_3_13_5_5_1_7_3_5_14_106.md`; SHA-256 `900c826532a72d114e44cf52b75253535e33f417d5f4a41ab8510feb3709eedd`

### Panel implementation and tests

- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_J0_same_camera_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_105_5/scripts/render_alapuse02v3n60_J0_same_camera_v99_11_7_13_3_13_5_5_1_7_3_5_14_105_5.py`; SHA-256 `4efc630dc1a7a62844076fc0102743cdd34e30a1a13dc33d7f826f4f8fdf9d69`
- `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_J0_same_camera_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_105_5/tests/test_J0_panel_direct_callback_lifecycle_v99_11_7_13_3_13_5_5_1_7_3_5_14_105_5.py`; SHA-256 `4c9c0e9140f995c4c60974268d9dbc4f39f78c4c86a7613a9d981241a453ab62`

## Scientific boundary

These internal losses validate this case only.  They are not CD, F5/F10,
intersection volume, reconstruction rate, MSSD, Co2, or silhouette IoU.
Paper comparisons require pinned evaluator commits, identical data/splits,
units, alignments, surface sampling, and failure accounting.
