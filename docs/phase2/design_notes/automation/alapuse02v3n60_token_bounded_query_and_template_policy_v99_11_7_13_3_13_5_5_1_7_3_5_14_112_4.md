# `alapuse02v3n60` token-bounded query order and template policy

## Status

- Case allowlist: `alapuse02v3n60` only.
- Model snapshot: `gpt-5.5-2026-04-23` with `reasoning.effort=high`.
- API: Responses with image input, strict Structured Outputs, `store=false`, and client `max_retries=0`.
- Normal completed semantic calls: 2. Recovery maximum: 3.
- Live API and CUDA are not authorized by this document transaction.

## Exact query order

1. `Q0` consumes only `cropped_input_path` and returns `object_category`, `visible_geometry`, `foundation_primary`, `foundation_recovery`, `gate_b`, `gate_d0`, and `confidence`.
2. Local foundation stages consume only their Q0 fields and write hash-pinned artifacts.
3. `Q1` consumes `combined_primary_evidence_path` and returns per-branch `verdict`, `reason_code`, `evidence_regions`, and `retry_authorized`.
4. Only failed branches consume their frozen recovery fields.
5. `Q2` consumes `combined_recovery_evidence_path` only when recovery ran. A repeated semantic failure sets `terminal_drop=true` before optimization.

## Template policy

- `foundation_primary` and `foundation_recovery` are consumer-keyed positive keyword lists: no prose, newline, or negative phrase.
- Gate B and Gate D0 retain their exact structured template owners; their fields are not guessed by the adapter.
- Hunyuan is image-only according to the structural receipt; no Q0 text is routed into the official Hunyuan call.
- auto-v2 Q1/Q2 see generated evidence only after it exists.
- Every rendered prompt records owner path/hash, rendered-text hash, consumer ID, template role, and attempt ID.

## Owner map

- `FOUNDATION_POLICY`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_2/candidates/foundation_primary_recovery_policy.json` (`32dc0f873e3f2f6e1c4522a6bab0fcc17e292a45579ead7dd0191f7644f998cf`).
- `Q0_MANIFEST`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_2/candidates/combined_crop_query_Q0_manifest.json` (`c43955fb8a507f5b24d189ae6b988037751d39fef93690ed31959faa1ec86dbc`).
- `JURY_POLICY`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_2/candidates/auto_v2_primary_and_recheck_jury_policy.json` (`abce6f2ef44195a8e669939cd3071ec0520d600a5299691181625392be50c3b8`).
- `QUERY_SCHEDULE`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_2/candidates/alapuse02v3n60_token_bounded_query_schedule.json` (`7adfc6f867b37d5f3f0a66325f7043b2f09a83e5a8dbbbc594b4a285303413ee`).
- `CONDITIONING_RECEIPT`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_2/owners/upstream_conditioning_contract.json` (`3521f07dd43458d9c56fe4e8fc7d069d12a4f47055727eb91d85b53e0d725801`).
- `PROMPT_REGISTRY`: `/home/fredcui/Projects/FollowMyHold/docs/prompt_templates/prompt_registry_manifest_v99_11_7_13_3_13_5_5_1_7_3_5_14_55.json` (`1a6c61ae4e125f169aac21e784f843a9ba845ccbc99aad2bc8dd373c60927546`).
- `GATE_B_OWNER`: `/home/fredcui/Projects/FollowMyHold/docs/prompt_templates/gate_b/Gate_B_original_crop_contact_proposal_prompt_v99_11_7_13_3_13_5_5_1_7_3_5_14_55.json` (`4b2048f393b7111573dbe2a2944df2cbe24f65f4f68f3620d9a3bc5887b4f081`).
- `GATE_D0_OWNER`: `/home/fredcui/Projects/FollowMyHold/docs/prompt_templates/gate_d0/Gate_D0_original_crop_contact_contract_prompt_v99_11_7_13_3_13_5_5_1_7_3_5_14_55.json` (`d294a7f55cd01373d2ebdb2d5c9fc3acbfd06ad77ea43c0bb027fc887c1f6d8f`).

## Public variables

- Input/provenance: `case_id`, `cropped_input_path`, `cropped_input_sha256`, `stage_id`, `attempt_id`, `owner_path`, `owner_sha256`, `frame`, `units`.
- Query state: `semantic_call_count`, `semantic_call_limit`, `transport_attempt`, `reservation_id`, `status`, `reason_codes`.
- Q0/Q1/Q2 fields are exactly those listed above; unknown fields are rejected.
- Branch state: `branch_id`, `accepted_sha256`, `immutable`, `semantic_attempt`, `reservation_spent`.
- API configuration stores only `model`, `reasoning_effort`, `store`, `max_retries`, and the environment-variable name `OPENAI_API_KEY`; never its value.

## Promotion gates

1. Exact nested schemas are compiled from the pinned owners and reject missing/unknown fields.
2. Mock normal/recovery/drop routes prove 2/3-call bounds and branch immutability.
3. A validate-only DAG proves every output-to-input edge with zero API/GPU work.
4. One live Q0 receipt is independently audited before any foundation or GPU launch.

## Corrected manual reference

- J0 panel: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_d0_J0_same_camera_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_105_5/panels/alapuse02v3n60_J0_same_camera_H1_O0_initial_final_joint_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_105_5.png` (`457f562ab001c73a5e6b6c92e4aff542444fcfe5108e39b75de89d33a0ec1733`).

## Official API boundary

GPT-5.5 supports image input, Responses, Structured Outputs, high reasoning, and snapshot `gpt-5.5-2026-04-23`: <https://developers.openai.com/api/docs/models/gpt-5.5>.
