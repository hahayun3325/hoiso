# Phase 0.17 — ARCTIC Paper-Style Evaluation Blockers

## Current status

The five ARCTIC default-vs-selector prediction pairs are available and clean enough for qualitative comparison.

GT-free proxy metrics have been computed for failure analysis.

## Important finding

The ARCTIC GT inventory found cropped image folders, but the required GT folders are missing or empty:

- `meta` exists but has zero files
- `raw_seqs` was not found
- `processed_seqs` was not found
- `splits` was not found
- `splits_json` was not found
- `object_vtemplates` was not found

## Provenance blocker

The selected images were renamed to:

- `abox01.jpg`
- `aket01.jpg`
- `ascis01.jpg`
- `alapuse01.jpg`
- `amicuse01.jpg`

They do not directly match `test_splits/arctic_test.csv`.

Therefore, we must recover each image's original ARCTIC source path:

`subject / sequence / view / frame`

before paper-style evaluation.

## Current decision

Do not report ARCTIC paper-style CD/F5/F10 yet.

Use ARCTIC for qualitative and GT-free proxy failure analysis until:

1. image provenance is recovered,
2. GT folders are installed and non-empty,
3. GT hand/object/camera overlay is visually validated for at least one case.
