# alapuse02v3n60: Gate-C to Object-Only Optimizer Entry Point

## Purpose

This note records how the project closed Gate-C hand placement, found the real FollowMyHold object/joint optimization dataflow, and prepared a reproducible transition toward joint refinement. It is a durable debugging and experiment-design reference; it does not claim final alignment success.

## Current scientific status

- Frozen hand: `s100_up`, 778 vertices, externally anchored through the proven camera/MoGe bridge.
- Accepted object: part-aware articulated laptop with preserved topology and a shared object root.
- Object-only checkpoint: technically valid, but visually rejected because the object and hand have implausible relative scale.
- Measured object/hand bounding-box diagonal ratio: approximately `14.1364`.
- Current decision: keep joint flow and Gate-D closed until shared-root scale/frame closure.

## Exact live entry point

- Pipeline: `/home/fredcui/Projects/FollowMyHold/third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines_v99_11_7_13_3_13_5_2_1_5.py`
- Caller: `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/run_v3_s100_up_existing_guidance_object_only_v99_11_7_13_3_13_5_2_1_5.py`
- Owner: pipeline `__call__`, line `1116`.
- Object-only loop: lines `1959–2064`.
- Update order: `object_optimizer.zero_grad()` at `1960`, `total_obj_loss.backward()` at `2051`, `object_optimizer.step()` at `2052`.
- Live external-anchor budget: `N=5`.
- Fast-track stage contract: hand/object/joint = `0/5/0`.
- Diagnostic continuation budgets: `5`, `10`, `20`.

## Why locating the entry point took so long

The difficulty was not one missing function. The runtime crossed a project repository, a nested Hunyuan vendor repository, versioned pipeline copies, package-local callers, generated case staging, and helper-mediated state restoration. Static validators repeatedly made assumptions that were narrower than the live dataflow.

The resolved incidents were:

1. **Search ownership:** the optimizer lived in the versioned Hunyuan pipeline, while early searches excluded or misclassified `third_party` sources.
2. **Update-sink recognition:** the live loop used alias/helper-mediated state and post-loop scheduler consumption; direct-method and recursive-loop validators produced false negatives.
3. **External-hand handoff:** the Gate-C hand existed in camera/MoGe coordinates but was not accepted by the pipeline until the 778-index similarity roundtrip and topology guard were proven.
4. **Repository boundary:** runtime vendor files were not tracked by the parent repository, so canonical tracked snapshots and versioned seams were required.
5. **Caller construction:** no directly reusable command existed. The real caller, package imports, `utilz` origins, task-list nesting, FOV, and seven semantic asset roles had to be bound.
6. **Configuration ownership:** the intended `0/5/0` contract was a run-local worker configuration, not a module global. Once the distinct worker config was derived, the no-model runtime capture passed.
7. **Filename and exception behavior:** exact leaf-name assumptions caused per-case exceptions that the outer process swallowed while returning success. Active-path and log-marker validation replaced return-code-only validation.
8. **Source identity:** the runtime hand donor differed from the frozen packet source. A topology-preserving, opt-in source rebinding helper closed the mismatch without relaxing scientific tolerance.
9. **Transform semantics:** the exact frozen packet target became authoritative; similarity replay was retained only as a diagnostic cross-check.
10. **Output ownership:** seven pipeline-owned outputs were valid; an eighth expected driver receipt was overdeclared and removed from the scientific completion contract.
11. **Visual adjudication:** the resulting pre-joint-flow geometry preserved the laptop but failed relative scale, proving that technical execution success is not scientific acceptance.
12. **Final source binding:** owner-scoped AST analysis identified the smallest enclosing loop of the exact zero/backward/step update sink and eliminated the last entry-point ambiguity.

## Important project artifacts

- Preparation packet: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_c_object_only_iteration_ablation/20260812_075033`
- Exact owner review: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_c_hand_anchor/professor_object_joint_prepare_v99_11_7_13_3_13_5_1_5_4/accepted_object_state_recovery_v99_11_7_13_3_13_5_1_5_5/path_shape_and_AST_node_recovery_v99_11_7_13_3_13_5_1_5_5_1/exact_gateA_object_binding_v99_11_7_13_3_13_5_1_5_5_2/object_only_launch_policy_v99_11_7_13_3_13_5_1_5_6/object_only_execution_v99_11_7_13_3_13_5_2/caller_filename_template_recovery_v99_11_7_13_3_13_5_2_1/lexical_config_binding_recovery_v99_11_7_13_3_13_5_2_1_5/inherited_whitespace_git_recovery_v99_11_7_13_3_13_5_2_1_5_1/object_only_replacement_execution_v99_11_7_13_3_13_5_2_2_5_2/runtime_source_identity_recovery_v99_11_7_13_3_13_5_2_2_5_2_1/owner_scoped_order_and_report_initialization_recovery_v99_11_7_13_3_13_5_2_2_5_2_2/numpy_JSON_boundary_recovery_v99_11_7_13_3_13_5_2_2_5_2_4/source_rebound_object_only_execution_v99_11_7_13_3_13_5_2_2_5_4_2/live_transform_semantics_recovery_v99_11_7_13_3_13_5_2_2_5_4_2_1/diagnostic_replay_object_only_execution_v99_11_7_13_3_13_5_2_2_5_4_3/seven_authoritative_output_recovery_v99_11_7_13_3_13_5_2_2_5_4_3_1/joint_flow_checkpoint_binding_v99_11_7_13_3_13_5_2_2_5_5_1/relative_scale_and_frame_recovery_v99_11_7_13_3_13_5_2_2_5_5_1_1/owner_scoped_object_loop_and_ablation_tools_v99_11_7_13_3_13_5_5_1_2/reports/owner_scoped_object_update_loop_v99_11_7_13_3_13_5_5_1_2.json`
- Preserved post-object checkpoint: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_c_hand_anchor/professor_object_joint_prepare_v99_11_7_13_3_13_5_1_5_4/accepted_object_state_recovery_v99_11_7_13_3_13_5_1_5_5/path_shape_and_AST_node_recovery_v99_11_7_13_3_13_5_1_5_5_1/exact_gateA_object_binding_v99_11_7_13_3_13_5_1_5_5_2/object_only_launch_policy_v99_11_7_13_3_13_5_1_5_6/object_only_execution_v99_11_7_13_3_13_5_2/caller_filename_template_recovery_v99_11_7_13_3_13_5_2_1/lexical_config_binding_recovery_v99_11_7_13_3_13_5_2_1_5/inherited_whitespace_git_recovery_v99_11_7_13_3_13_5_2_1_5_1/object_only_replacement_execution_v99_11_7_13_3_13_5_2_2_5_2/runtime_source_identity_recovery_v99_11_7_13_3_13_5_2_2_5_2_1/owner_scoped_order_and_report_initialization_recovery_v99_11_7_13_3_13_5_2_2_5_2_2/numpy_JSON_boundary_recovery_v99_11_7_13_3_13_5_2_2_5_2_4/source_rebound_object_only_execution_v99_11_7_13_3_13_5_2_2_5_4_2/live_transform_semantics_recovery_v99_11_7_13_3_13_5_2_2_5_4_2_1/future_run_v99_11_7_13_3_13_5_2_2_5_3_3/post_object_before_joint_flow/checkpoint_v99_11_7_13_3_13_5_2_2_5_3_3.pt`
- Budget review: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_c_object_only_iteration_ablation/20260812_075033/exact_N_step_zero_and_durable_note_v99_11_7_13_3_13_5_5_1_3/reports/exact_object_budget_N_v99_11_7_13_3_13_5_5_1_3.json`
- Step-zero source review: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_c_object_only_iteration_ablation/20260812_075033/exact_N_step_zero_and_durable_note_v99_11_7_13_3_13_5_5_1_3/reports/step_zero_source_contract_v99_11_7_13_3_13_5_5_1_3.json`
- Source slice: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_c_object_only_iteration_ablation/20260812_075033/exact_N_step_zero_and_durable_note_v99_11_7_13_3_13_5_5_1_3/evidence/object_entrypoint_and_step_zero_source_slice_v99_11_7_13_3_13_5_5_1_3.txt`

## What the object-only stage does and does not do

The object-only loop freezes the accepted hand while updating object-side variables using image/flow evidence. The bound loop contains no explicit hand, contact, collision, or penetration term. Therefore it can improve object evidence and gross pose but is not guaranteed to move the object toward the hand. Hand-relative scale and distance are currently evaluation signals.

## Current experiment contract

1. Bind the exact zero-update state before the first object optimizer step.
2. If step zero is already misscaled, skip longer iteration testing and repair the shared metric/root transform while preserving articulation and topology.
3. If step zero is plausible and the first `5` steps improve hand-relative and object evidence without converging, run one continuous `20`-step diagnostic with checkpoints at `5`, `10`, and `20`.
4. If object evidence improves while hand-relative geometry worsens, revise the objective or scale/frame bridge rather than adding iterations.
5. Enter joint flow only from the smallest stable checkpoint inside the v6-calibrated capture envelope.
6. Run Gate-D contact/penetration cleanup only after joint flow produces a valid interaction state.

## Unresolved item

Step-zero status: `source_only_preloop_writer_required`. The next implementation action is to bind an existing pre-loop writer or add one small versioned source-only hook, statically audit it, and freeze a zero-update capture command before any new GPU authorization.

## Reproducibility rules

- Use fresh, non-overwriting output roots.
- Freeze exact source hashes, input hashes, seed, optimizer state, learning rates, active losses, and checkpoint schedule.
- Treat the first stable acceptable checkpoint as the result; do not select by final iteration alone.
- Preserve the accepted articulated object, hand vertex order, hand faces, camera, and frozen hand target.
- Validate authoritative outputs rather than wrapper-owned convenience receipts.
- Never advance solely because the child process returns success.
