# Hand solver selection and entry requirements

Status reviewed on 2026-09-08 for `alapuse02v3n60`.

Use the explicit hand-specific Frame-I route for the next bounded native-hand candidate. Do not let missing settings select the historical alignment route. The native candidate and complete original-image entry are **not yet accepted or connected**; this note records the intended route and its prerequisites, not a production-ready default.

## Solver registry

| Role | Server-verified repository path | Selection rule |
|---|---|---|
| Intended native-hand candidate solver | `tools/gate_c_v99_11_hand_anchor/run_v7_CPU_hand_specific_frame_I_registration.py` | Bind this exact source and a reviewed, case-owned policy explicitly. |
| Historical alignment solver | `tools/gate_c_v99_11_hand_anchor/run_v3_CPU_7DoF_global_hand_alignment_v99_11_7_13_3_6.py` | Retain for pinned historical records. Never use as an automatic fallback for a new native-hand run. |
| Historical policy | `config/automation/alapuse02v3n60_selected_hand_CPU_7DoF.json` | Retain exact bytes and path for existing receipts; do not pair it with the native solver. |

Verified source hashes:

- Native solver: `3636bb253ed45fb3780735433735dc14d0ba1ab77e79d3b3ebd076a65613077b`.
- Historical solver: `feaeb2a5e2531da413b7229f7d13d4402f693f9214927f8a829f61ca2a8bab7c`.
- Historical policy: `fe31da62fe24abf86fd01486feab00b09c70daf41506f755c350c846993371fb`.

These paths and hashes come from returned server evidence. Publishing this note does not install the solver, prove that every source file has been pushed, or establish the current server checkout. If a file is missing or its hash differs, inspect that change rather than substituting a similarly named version.

## Mandatory entry bindings

The foundation builder must receive both `HAND_FRAME_I_SOLVER_SCRIPT` and `HAND_FRAME_I_POLICY_TEMPLATE`. Missing either value, missing both, a legacy pairing, a changed hash, or a case/frame mismatch must stop before any work is loaded. Enforce the same rule on primary, recovery and resume paths.

The current registration wrapper can launch ViTPose before it checks the native policy. Put the entry guard before loading or calling that wrapper. A disabled policy checked after an image model launches is too late. Guards have been tested in staging; live installation is still pending.

Each run must bind the selected hand, saved candidate, independent image target, MoGe points, hand mask, coordinate convention and policy by path and hash. Inspect actual emitted arguments. A successful configuration rehearsal or a list of output filenames does not prove live execution, rendered geometry or completed-result reuse.

## Joint order and supported policy

The reviewed HaMeR wrapper already exports joints in OpenPose order. The corresponding right-hand ViTPose target uses the same order: wrist/root, thumb, index, middle, ring and little finger, with four landmarks per finger. The native solver indexes the saved joints using `joint_map_21`; applying the wrapper's permutation a second time mislabels those joints.

Step 0CV v11b verified this on the actual saved packet using one CPU MANO forward evaluation from its saved pose matrices and shape. Vertex coordinate RMSE was `1.9535896252131864e-08 m`, and joint coordinate RMSE was `1.735565898517664e-08 m`. Applying the old permutation again produced joint coordinate RMSE `0.035045805371859015 m`. These are replay/order comparisons, not registration accuracy measurements or proof of the cause of a previous jury verdict.

For this verified packet, use `joint_map_21 = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]`. The staged disabled policy `native_hand_radius7_openpose_disabled.json` has SHA256 `622f6aaa4cbd7f59a10e2b0623a45b3a57d9fe59de975acb68bb711c71c8f3d2`. Do not infer an identity map for another producer or packet without equivalent provenance checks. Detector candidate index 1 and saved batch index 0 are distinct index spaces.

The reviewed support radius is seven pixels: it supplies nine anchors on this input, while radius four supplies six. Minimum anchors remains eight. Keep the existing quality limits, including keypoint NRMSE 0.15, anchor NRMSE 0.35, surface NRMSE 0.5, positive-depth fraction 0.95 and projected-mask fraction 0.5. Neither sufficient anchors nor correct joint naming proves correct placement.

The staged policy remains disabled. A bounded diagnostic trial needs its own input-bound claim and run-owned execution policy; it must not modify the disabled source policy or authorize installation, Frame I or contact optimization. The native solver fits global scale, root rotation and translation with MANO shape, articulation and topology frozen. It is not an articulated-pose refinement step.

## Frame and evidence requirements

The solver's internal `native_MoGe` label means the exported MoGe PLY basis. The saved native object H2M transform also targets that basis. Do not apply an extra Y/Z flip when comparing those hand and object outputs.

The conversion to raw EXR camera coordinates is `C = diag(1, -1, -1, 1)`. Use `C @ T_saved` only when converting an object-to-PLY transform into the raw camera frame. Do not apply the object's H2M transform to the hand. Hand placement must be solved against its own target/support.

Future H2M evidence must visibly contain the transformed object and its actual scene target with common axes and scale. A matrix filename beside an isolated hand rendering is insufficient. Image panels must identify the selected hand and the actual crop/mirror frame. Diagnostic wireframes or displays are not a replacement for a complete jury-evidence renderer.

## Acceptance, reuse and retirement

The original Q2 remains terminally `REJECT_CASE`. Source fixes, diagnostics and a passing candidate do not reopen that transaction or authorize another recovery. Preserve its request, response, evidence and completion. Any future evaluation requires a separately reviewed lifecycle.

The achieved 0CP pipeline starts from accepted foundation and hand inputs and reaches downstream review with completed reuse. Full original-crop integration, fresh downstream geometry/semantic bindings and J0 acceptance remain unfinished. Verify the original case before testing `blapuse02v4n344`.

Keep historical solver and policy files at their pinned live paths until dependency migration and corrected entry execution/reuse have been verified. Copied review ZIPs do not replace installed dependencies. Prevent accidental selection through dispatch rules first; delete only explicitly disposable files after dependency review.

Evidence: `step_0cv_saved_joint_order_replay_v11b_review.zip`, SHA256 `60e4a454a0bcab3f6ee0d34a8d2130d44e433800e91aadc5d6364025961d7309`; 12 payload hashes and 15 checks passed, with 554 paths preserved. No pose fit, image-model inference, jury call or State change occurred in that replay.
