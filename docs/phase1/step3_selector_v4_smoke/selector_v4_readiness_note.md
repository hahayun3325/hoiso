# Selector-v4 implementation readiness note

## Current status

Selector-v4 has passed the offline dry-run and smoke decision check.

The implementation config now points to the clean case-config manifest:

`/home/fredcui/foho_phase0/phase1_diagnostics/config_audit/selector_v4_case_config_manifest_clean.csv`

The smoke check contains four representative cases:

- `alapuse01`: expected clean selected case
- `abox01`: expected severe penetration reject
- `aket01`: expected severe floating reject
- `oakink_split000`: expected borderline/floating reject

The smoke decision check produced 4 / 4 matching decisions.

## Interpretation

Selector-v4 is ready to be tested as a log-only pipeline gate. It should not overwrite pipeline outputs yet. The next test should run selector-v4 automatically after candidate generation and write decision JSON files.

## Next action

Run selector-v4 in log-only mode on a small set of representative cases. If the decisions match the offline study, then selector-v4 can be connected to the pipeline as a post-candidate verification gate.
