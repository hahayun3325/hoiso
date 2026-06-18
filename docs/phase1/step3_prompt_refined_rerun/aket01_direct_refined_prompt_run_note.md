# aket01 direct refined-prompt rerun note

## Why aket01 first

`aket01` is selected as the first reject-and-rerun test because its previous failure reason was `severe_floating`, and the object category is simpler than scissors or microwave. The refined prompt emphasizes the full ketchup bottle body, narrow neck, cap, wider rounded-rectangular body, smooth sides, and negative constraints.

## Attempt 0

Use:

`/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_aket01_partaware_v2/attempt0_partaware_prompt/object_prompt_partaware_v2.txt`

Run:

1. inpainting with the refined prompt;
2. Hunyuan object initialization;
3. object pose optimization;
4. selector-v4 recheck.

Expected selector-v4 outcome:

- pass: `accepted_after_prompt_refined_rerun`
- fail: continue to Attempt 1

## Attempt 1

Use the same refined prompt or a failure-specific variant and rerun object inpainting once.

Expected selector-v4 outcome:

- pass: `accepted_after_reinpaint`
- fail: `failed_after_reinpaint`

Do not overwrite previous Phase 0 or Phase 1 outputs.
