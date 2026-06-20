# ARCTIC-5 automatic comparison plan

## Goal

Run a controlled automatic comparison study over the five selected ARCTIC cases.

The goal is not to overwrite final outputs immediately. The goal is to compare:

1. default baseline
2. old GPT-5.5 / selector-v1 output
3. selector-v4 initial decision
4. prompt-refined rerun attempt0
5. reinpaint fallback attempt1 if needed

## Cases

- `abox01`
- `aket01`
- `ascis01`
- `alapuse01`
- `amicuse01`

## Policy

- If selector-v4 accepts an original candidate, keep it.
- If selector-v4 rejects both original candidates, run direct part-aware prompt attempt0.
- If attempt0 passes selector-v4 recheck, mark `accepted_after_prompt_refined_rerun`.
- If attempt0 fails, run one reinpaint fallback.
- If fallback passes, mark `accepted_after_reinpaint`.
- If fallback fails, mark `failed_after_reinpaint`.

## Safety rule

Never overwrite old Phase 0 or Phase 1 outputs. All automatic comparison outputs must go under a new experiment root.

## Suggested experiment root

`/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_automatic_comparison`

## Required outputs per case

- rerun state JSON
- mesh registration report
- selector-v4 recheck metrics
- visual comparison panel
- final status label
