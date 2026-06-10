# Phase 0.17 — ARCTIC Paper-Eval Next Gate

## Current answer

The selected ARCTIC candidates are not ready for paper-like quantitative evaluation yet.

## What is already ready

- Clean default-vs-selector prediction pairs
- Qualitative comparison panel
- GT-free proxy metrics
- Mostly recovered image provenance

## Remaining blockers

1. Exact provenance must be finalized for `abox01` and `ascis01` using pixel comparison.
2. ARCTIC GT folders are still missing or empty.
3. Download logs show authentication failures.
4. The readiness checker must include the `unpack/arctic_data/data` directory.
5. At least one GT overlay must be visually validated.

## First paper-eval target after GT is ready

Start with:

`aket01 = s01/ketchup_grab_01/view 7/frame 147`

because the provenance is exact and the object is simpler than scissors/laptop/microwave.
