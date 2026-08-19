# `alapuse02v3n60` automatic-pipeline implementation proposal

## Status and scope

- Case allowlist: `alapuse02v3n60` only.
- Accepted manual J0/F0 output remains immutable.
- Normal GPT-5.5-high budget: Q0 + Q1 = 2 calls; recovery maximum: Q0 + Q1 + Q2 = 3 calls.
- No human terminal gate; F0 and the fixed evaluator own completion.
- This note authorizes candidate implementation and mocked tests, not a live API/GPU launch.

## Design

1. Validate the case manifest, owner hashes, crop, frames, units, and secret presence.
2. Q0 sends the original crop once and returns strict nested foundation, Gate-B, and Gate-D0 fields.
3. Emit typed JSON and the FollowMyHold-compatible `image_id,image_path,response` CSV.
4. Run foundation branches locally and write immutable provenance receipts.
5. Q1 judges one labeled multi-branch evidence sheet; retry failed branches only.
6. Q2 conditionally rechecks only recovered branches; a second semantic failure drops the case.
7. Run Gate A, CPU hand registration, Gate C, contract compilation, H0, H1, O0, J0, F0, and evaluation.
8. Export final checkpoint, metrics JSON/CSV, panel, runtime, VRAM, API usage, and failure accounting.

## Planned source owners

- `src/foho/automation/contracts.py`
- `src/foho/automation/openai_query_adapter.py`
- `src/foho/automation/prompt_registry.py`
- `src/foho/automation/evidence_sheet.py`
- `src/foho/automation/branch_retry_controller.py`
- `src/foho/automation/stage_adapters.py`
- `src/foho/automation/orchestrator.py`
- `src/foho/automation/run_alapuse02v3n60.py`
- `config/automation/alapuse02v3n60_automatic_manifest.json`
- matching `tests/automation/` fixtures.

## Existing query/prompt owners

- Foundation primary/recovery policy: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_2/candidates/foundation_primary_recovery_policy.json` (`32dc0f873e3f2f6e1c4522a6bab0fcc17e292a45579ead7dd0191f7644f998cf`).
- Combined Q0 manifest: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_2/candidates/combined_crop_query_Q0_manifest.json` (`c43955fb8a507f5b24d189ae6b988037751d39fef93690ed31959faa1ec86dbc`).
- auto-v2 Q1/Q2 policy: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_2/candidates/auto_v2_primary_and_recheck_jury_policy.json` (`abce6f2ef44195a8e669939cd3071ec0520d600a5299691181625392be50c3b8`).
- Query schedule: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_2/candidates/alapuse02v3n60_token_bounded_query_schedule.json` (`7adfc6f867b37d5f3f0a66325f7043b2f09a83e5a8dbbbc594b4a285303413ee`).
- Upstream conditioning proof: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_2/owners/upstream_conditioning_contract.json` (`3521f07dd43458d9c56fe4e8fc7d069d12a4f47055727eb91d85b53e0d725801`).
- Prompt registry: `/home/fredcui/Projects/FollowMyHold/docs/prompt_templates/prompt_registry_manifest_v99_11_7_13_3_13_5_5_1_7_3_5_14_55.json` (`1a6c61ae4e125f169aac21e784f843a9ba845ccbc99aad2bc8dd373c60927546`).
- Gate-B owner: `/home/fredcui/Projects/FollowMyHold/docs/prompt_templates/gate_b/Gate_B_original_crop_contact_proposal_prompt_v99_11_7_13_3_13_5_5_1_7_3_5_14_55.json` (`4b2048f393b7111573dbe2a2944df2cbe24f65f4f68f3620d9a3bc5887b4f081`).
- Gate-D0 owner: `/home/fredcui/Projects/FollowMyHold/docs/prompt_templates/gate_d0/Gate_D0_original_crop_contact_contract_prompt_v99_11_7_13_3_13_5_5_1_7_3_5_14_55.json` (`d294a7f55cd01373d2ebdb2d5c9fc3acbfd06ad77ea43c0bb027fc887c1f6d8f`).

## Accepted manual-reference assets

- H0 call arguments: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_intermediate_Hshape_recovery_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_10_2/config/alapuse02v3n60_corrected_H0_call_arguments_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_10_2.json` (`6c5aa00765f1e7ffc15b43a93796b573f166815bec73130fa00f796647ee078b`).
- H0 checkpoint: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H0_corrected_five_update_v99_11_7_13_3_13_5_5_1_7_3_5_14_88_7_1/runtime/controller/checkpoints/H0_step_005.pt` (`8e382d5f712e520970e558d3c8cedf158d65e2281afc6ed99e4fd02cac926eb6`).
- H1 checkpoint: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_H1_fixed_registration_five_attempt_v99_11_7_13_3_13_5_5_1_7_3_5_14_93_2/runtime/controller/checkpoints/H1_attempt_005.pt` (`f21a0ac081d6eb282f9d77e610faa99367f7d6174c1ca3a1d8399f956d482f4b`).
- O0 checkpoint: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_O0_five_attempt_v99_11_7_13_3_13_5_5_1_7_3_5_14_98/runtime/controller/checkpoints/O0_attempt_005.pt` (`b6a5adf128be9a3bec622bc5d23c590942d7b137984f5879d75f2aed9ed86a64`).
- J0 terminal checkpoint: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_J0_evaluation_v99_11_7_13_3_13_5_5_1_7_3_5_14_104_3/checkpoints/J0_terminal_accepted_v99_11_7_13_3_13_5_5_1_7_3_5_14_104_3.pt` (`d062194c0a84a3acbc910eaf5d4a8c81027e3703217e3a1fe0613d17b5c7ee7a`).
- J0 metric JSON: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_J0_evaluation_v99_11_7_13_3_13_5_5_1_7_3_5_14_104_3/reports/J0_trajectory_and_metric_delta_v99_11_7_13_3_13_5_5_1_7_3_5_14_104_3.json` (`78854b5e8deaed0c58342372a8e7f57fe2b91cebc5d1b516b7b6fe509ef3a182`).
- J0 attempt CSV: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_J0_evaluation_v99_11_7_13_3_13_5_5_1_7_3_5_14_104_3/reports/J0_attempt_trajectory_v99_11_7_13_3_13_5_5_1_7_3_5_14_104_3.csv` (`9b1f921c6073450a4837f62abc3f3cb735f5192d6805b59d8092dbc1164318d2`).
- J0 final panel: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_J0_same_camera_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_105_5/panels/alapuse02v3n60_J0_same_camera_H1_O0_initial_final_joint_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_105_5.png` (`457f562ab001c73a5e6b6c92e4aff542444fcfe5108e39b75de89d33a0ec1733`).

## Existing optimization owners

- J0 manifest: `/home/fredcui/Projects/FollowMyHold/config/optimization/alapuse02v3n60_J0_case_manifest_v99_11_7_13_3_13_5_5_1_7_3_5_14_100_2.json` (`acc3d0aa04232162161360074c1697ba850504731c50e4398505471257300912`).
- J0 live binder: `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/j0_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_100_2.py` (`6b68fa28281a4a2b003bb0875eb91cb0b279aac307b1509f2deb4343ec6a2aee`).
- Shared guidance caller: `/home/fredcui/Projects/FollowMyHold/src/foho/guidance/run.py` (`4b0c454ac29ff4d30b120a9d3546fed6cecbef5b68efdc51eb63381e7d9ac090`).

## Variable contract

- Provenance: `case_id`, `stage_id`, `attempt_id`, `owner_path`, `owner_sha256`, `input_paths`, `input_sha256`, `output_paths`, `output_sha256`, `frame`, `units`, `status`, `reason_codes`.
- Q0: `object_category`, `visible_geometry`, `foundation_primary`, `foundation_recovery`, `gate_b`, `gate_d0`, `confidence`.
- Q1: `branch_id`, `verdict`, `reason_code`, `evidence_regions`, `retry_authorized`.
- Q2: `branch_id`, `verdict`, `reason_code`, `terminal_drop`.
- Branch state: `semantic_attempt`, `transport_attempt`, `accepted_sha256`, `immutable`, `reservation_authorized`, `reservation_spent`.
- H0: `global_hand_rotation`, `global_hand_translation`.
- H1: accepted MANO residual including `selected_so3_residual` over inherited H0 rigid state.
- O0: `global_object_rotation`, `global_object_translation`, with H1 hand frozen.
- J0 terminal: `global_hand_rotation`, `global_hand_translation`, `global_object_rotation`, `global_object_translation`; H1 articulation remains frozen.
- API: environment variable name `OPENAI_API_KEY`, snapshot `gpt-5.5-2026-04-23`, `reasoning.effort=high`, `store=false`; never serialize the secret value.

## Promotion gates

1. Candidate schemas compile and reject unknown/missing fields.
2. Mocked Q0 produces typed JSON and exact legacy CSV.
3. Mocked normal, recovery-PASS, and recovery-FAIL routes obey 2/3-call budgets.
4. Accepted branches remain hash-identical during another branch's recovery.
5. `--validate-only` closes every stage edge with zero API/GPU work.
6. One live Q0 receipt is inspected before foundation execution.
7. The automatic final packet is compared semantically with the accepted manual reference before any other case is authorized.

## Official API boundary

GPT-5.5 accepts image input and supports Structured Outputs through the Responses API: <https://developers.openai.com/api/docs/models/gpt-5.5>. The adapter uses a strict schema rather than legacy JSON mode and stores only request metadata, usage, hashes, and normalized output.
