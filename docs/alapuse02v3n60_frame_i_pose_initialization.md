# Frame-I hand-specific pose initialization for `alapuse02v3n60`

## Scope and pipeline boundary

This document records the initial-pose algorithm closed in worksheet 0.0.4. The stage is **Frame I** (occasionally written informally as “F1”); there is no separate F1 stage in the current DAG.

The closed initialization chain is:

`Gate A -> Frame I -> zero-update Gate C`

- Gate A owns the accepted object parts and intended semantic region.
- Frame I selects, places, validates, and publishes the hand in the same documented frame as the fresh object parts.
- Gate C performs a semantic consistency check with zero optimization updates and makes the result eligible for D0.
- D0 and the subsequent H0/H1, O0, J0, F0, export, and evaluation steps are outside this document and belong to the next worksheet.

## Why the previous route was insufficient

The historical route treated the hand as though the object-owned Hunyuan-to-MoGe transform and whole-object registration could also own the hand. For this articulated laptop case, a globally attractive object alignment could associate the hand-side evidence with `keyboard_base`, use the wrong camera convention, or produce an implausible hand scale/root. The object transform therefore cannot be reused as the hand transform.

## Intuitive description of the new algorithm

The algorithm is a tightly owned hand-placement route, not merely a larger numerical penalty:

1. Preserve the Q0-selected hand identity and box.
2. Use the selected SAM2 mask so geometric anchors cannot wander outside the chosen hand.
3. Use the side-matched 21-point ViTPose target and the saved HaMeR/MANO hand parameters.
4. Use native MoGe point-map evidence and the MoGe-owned camera inside the projection objective. Do not substitute the saved positive-camera hand camera or the object-only H2M matrix.
5. Fit a bounded hand-specific Sim(3) scale/root transform. For this case, the smallest passing selected-mask anchor window is `anchor_window_radius_px = 7`; `minimum_anchor_joints = 8` remains unchanged.
6. Require finite 778-vertex MANO topology, positive depth, proper positive transform, non-saturated scale, metric-anchor support, symmetric surface support, and selected-mask support.
7. Replay the saved MANO parameters with the source-faithful MANO operator to verify the saved vertices and articulated joints. Do not use `J_regressor @ final_posed_vertices` as an articulated-joint identity test.
8. Apply the explicit CPU-adequate semantic rule: the active index/middle fingertips and hand must be near `screen_lid` and preferentially closer to it than `keyboard_base`. The accepted three-view panel is part of this evidence.
9. Publish the accepted hand and the two fresh object parts as an exact eight-file, hash-owned Frame-I inventory. Normalize owner comparison by canonical path/hash identity so nonidentity metadata cannot create a false mismatch.
10. Re-enter the restartable DAG from a clean Gate-A checkpoint, publish Frame I exactly once, render without state mutation, then let Gate C validate the binding with zero updates.

The numerical keypoint NRMSE remains `0.29848690841524667` against the historical strict-fit threshold `0.15`; it is recorded as diagnostic rather than silently changed. The accepted route instead requires the full transform, scale, mask, 3D, part-preference, owner-lineage, and human-reviewed proximity contract. For context, selected-mask support is `0.9010282776349614`, metric-anchor NRMSE is `0.1556058452447587`, surface NRMSE is `0.0858038193038591`, and positive-depth support is `1.0`.

## Relationship to Gate C

Frame I is the mover and publisher. It determines the hand-specific transform and writes the accepted hand/part/finger/D0-seed binding. Gate C is not another fitter. It reads those published owners and checks that they still mean “index and middle near `screen_lid`,” that the keyboard is excluded, and that no semantic identity changed during publication. Its successful terminal must report `optimization_updates: 0`, `eligible_for_d0: true`, active fingers `index` and `middle`, and active part `screen_lid`.

## Important repository scripts

- `src/foho/automation/selected_hand_registration.py`: selected-hand solver wrapper, policy loading, output controls, and registered-hand publication.
- `src/foho/automation/foundation_manifest.py`: manifest wiring for the selected hand and run-owned policy/config overrides.
- `src/foho/automation/case_runner.py`: case-level selected-hand invocation and owner transport.
- `src/foho/automation/post_q2_runner.py`: restartable Gate-A/Frame-I/Gate-C DAG and stage transitions.
- `src/foho/automation/frame_i_gate_c_adapter.py`: Frame-I publication, canonical owner normalization, accepted-hand binding, and zero-update Gate-C adapter.
- `src/foho/automation/selected_hand_hamer.py`: saved HaMeR/MANO candidate production and selected-hand ownership.
- `src/foho/preprocess/segment_hoi_sam2.py`: selected hand/object mask evidence.
- `src/foho/preprocess/get_hunyuan_input.py`: foreground-owned MoGe input preparation.
- `src/foho/geometry/moge.py`: native MoGe points and camera evidence.
- `tools/gate_c_v99_11_hand_anchor/run_v3_CPU_7DoF_global_hand_alignment_v99_11_7_13_3_6.py`: historical bounded CPU alignment patterns and diagnostics.
- `tools/gate_c_v99_11_hand_anchor/extract_case_image_vitpose_target_v99_11_7_9_21_7_2.py`: ViTPose target extraction/order owner.
- `tests/automation/test_selected_hand_frame_i_registration.py`: hand-specific solver and contract tests.
- `tests/automation/test_selected_hand_frame_i_promotion.py`: installed/default/override promotion tests.
- `tests/automation/test_frame_i_gate_c_adapter.py`: publication, normalization, and Gate-C adapter tests.
- `tests/automation/test_post_q2_runner.py`: restart/DAG transition tests.

## Important installed and run-owned paths

- Project root: `/home/fredcui/Projects/FollowMyHold`
- Python: `/home/fredcui/anaconda3/envs/foho/bin/python`
- Case root: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2`
- Worksheet run root: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/tracehoi_autopipeline_0_0_4_20260829T200846Z`
- Installed default policy: `config/automation/alapuse02v3n60_selected_hand_frame_i.json`
- Complete owner-root runtime config: `$RUN_ROOT/config/alapuse02v3n60_post_q2_frame_i_complete_owner_roots.json`
- Normalized Frame-I/Gate-C activation: `$RUN_ROOT/config/alapuse02v3n60_accepted_lid_frame_i_gate_c_normalized_v1.json`
- Normalized live root: `$RUN_ROOT/live/accepted_lid_frame_i_owner_normalized_v2`
- State: `$NORMALIZED_ROOT/state.json`
- Frame-I terminal: `$NORMALIZED_ROOT/01_frame_i/frame_i_runtime/frame_i_terminal.json`
- Accepted publication root: `$NORMALIZED_ROOT/01_frame_i/frame_i_runtime/accepted_cpu_lid_proximity_v1`
- Gate-C terminal: `$NORMALIZED_ROOT/02_gate_c/gate_c_runtime/gate_c_terminal.json`
- Diagnostic render: `$RUN_ROOT/renders/alapuse02v3n60_normalized_frame_i_hand_parts_patch.png`

The accepted publication root contains exactly:

- `accepted_H2M.npy`
- `accepted_frame_i_gate_c_binding.json`
- `accepted_hand_in_I.ply`
- `fresh_keyboard_base_in_I.ply`
- `fresh_screen_lid_in_I.ply`
- `fresh_whole_object_in_I.ply`
- `screen_lid_local_D0_seed.ply`
- `screen_lid_local_D0_seed_face_ids.npy`

## Important variables and invariants

- `PROJECT_ROOT`: active repository root.
- `CASE_ROOT`: stable case owner.
- `RUN_ROOT`: immutable worksheet-0.0.4 run owner selected by `tracehoi_autopipeline_0_0_4_active_root.txt`.
- `NORMALIZED_ROOT`: restartable live DAG root.
- `NORMALIZED_STATE`: stage history and `next_index` owner.
- `NORMALIZED_FRAME_I_TERMINAL`: closed Frame-I decision and Gate-C eligibility.
- `NORMALIZED_ACCEPTED_ROOT`: exact published geometry/binding inventory.
- `NORMALIZED_GATE_C_TERMINAL`: zero-update semantic terminal and D0 eligibility.
- `NORMALIZED_RUNTIME_CONFIG`: complete resolved path/hash owners.
- `NORMALIZED_ACTIVATION_CONFIG`: accepted-lid route selection and installed-source hashes.
- `PYTHON_BIN`: `/home/fredcui/anaconda3/envs/foho/bin/python`; the 4090 server does not use Miniconda.
- `CUDA_VISIBLE_DEVICES=""`: CPU-only audit/initialization boundary.
- `PYTHONDONTWRITEBYTECODE="1"`: prevent incidental source-tree bytecode writes.
- `candidate_execution_authorized`: remains false in the installed default policy; only an exact run-owned, hash-audited policy may enable one bounded call.
- `anchor_window_radius_px = 7` and `minimum_anchor_joints = 8`: smallest passing local selected-mask support for this case.
- `active_fingers = ["index", "middle"]` and `active_object_part = "screen_lid"`: frozen semantic owners.

Every live call uses a fresh, atomically written claim. A claim is permanent even when the child fails; the same live root is never retried. Detached testing, independent reproduction, transactional installation/rollback, run-owned activation, state-only checkpoint materialization, one-call authorization, execution, postflight audit, rendering, and Gate-C validation are separate lifecycle boundaries.

## Closed outputs and visual evidence

- Frame-I terminal SHA-256: `2bffc15346a6d5843dd6016ce8083c4e6068a9ad3b0a4a5be317439462254efa`
- Pre-Gate-C state SHA-256: `43b0456d8fe328865fe07cf2e36c697dcbe0a4f84c4233ea95d1dfab16f3d132`
- Diagnostic render SHA-256: `6cf423a54ce0b1cca8d90118a07f6dc0499dba06f22ea7cfa89854074488d960`
- Reviewed local copy: `/Users/fredcui/Downloads/alapuse02v3n60_normalized_frame_i_hand_parts_patch.jpg`
- Human/machine acceptance label: `accepted_near_screen_lid`

The three views place the hand at the lid edge and away from the keyboard base. This is adequate for initial CPU placement under the agreed rule; it is not a claim of exact physical contact. Fine contact and transformation refinement remain downstream algorithm work.

## Next phase

Worksheet 0.0.4 ends after zero-update Gate C and this documentation. A later worksheet 0.0.5 should start from the fresh Gate-C terminal and `screen_lid_local_D0_seed_face_ids.npy`, implement the real D0 semantic-to-objective compiler, bind the index/middle contact pads while excluding `keyboard_base`, prove the memory boundary, and only then feed H0/H1. It must not regenerate the initial hand pose merely because downstream optimization begins.
