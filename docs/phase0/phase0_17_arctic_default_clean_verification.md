# Phase 0.17 — ARCTIC Default Clean Verification

## Result

The five ARCTIC default runs are clean enough for qualitative default-vs-selector comparison.

The purity audit shows:

- default configs point to `arctic_<case>_default`
- `FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR="0"`
- selector export/debug dirs are empty
- no selector/debug lines appear in default logs
- each case has `Reconstructed object` and `Finished processing all images`

The clean verifier reports:

- `pair_ok=True`
- `clean_pair_ok=True`

for all five cases.

## Important caution

The current shell environment still had selector variables from a previous GPT-5.5 selector run. This does not invalidate the completed default logs, but future runs should unset selector-related variables before running default baselines.

## Current use

The ARCTIC default-vs-selector panel can be used for qualitative failure-mode analysis.

It should not yet be used for paper-style quantitative metrics because ARCTIC GT hand/object/camera annotations are not resolved yet.
