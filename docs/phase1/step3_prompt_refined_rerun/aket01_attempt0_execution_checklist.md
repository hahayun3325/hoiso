# aket01 attempt0 direct refined-prompt execution checklist

## Input

Case: `aket01`

Prompt:

`/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_aket01_partaware_v2/attempt0_partaware_prompt/object_prompt_partaware_v2.txt`

Previous failure:

`severe_floating`

## Attempt 0 pipeline

1. Use the part-aware v2 prompt directly.
2. Rerun object inpainting.
3. Rerun Hunyuan/object initialization.
4. Rerun object pose optimization.
5. Export new hand/object aligned meshes to a new non-overwriting directory.
6. Run selector-v4 recheck on the new result.

## Expected outcome

- If selector-v4 passes: mark as `accepted_after_prompt_refined_rerun`.
- If selector-v4 fails: proceed to `attempt1_reinpaint_fallback`.
- If attempt1 still fails: mark as `failed_after_reinpaint`.

## Important rule

Do not overwrite previous Phase 0 or Phase 1 outputs.
