# Phase 0.17 — ARCTIC Salvage Cleanup

## Problem

The first ARCTIC GPT-5.5 auto-selector runs accidentally wrote outputs into:

`/home/fredcui/foho_phase0/runs/oakink000_gpt55_short`

because the generated ARCTIC configs originally had the wrong `BASE_DIR`.

## Salvage

The ARCTIC case files were copied from the polluted OakInk run folder into the correct ARCTIC folders:

- `arctic_abox01_gpt55_auto`
- `arctic_aket01_gpt55_auto`
- `arctic_ascis01_gpt55_auto`
- `arctic_alapuse01_gpt55_auto`
- `arctic_amicuse01_gpt55_auto`

The copy was recorded in:

`salvage_manifest_all_arctic_from_oakink000_gpt55_short.json`

## Cleanup rule

Do not delete the whole OakInk run folder.

Only delete source paths listed in the salvage manifest after verifying that the copied destination exists and has the same file size.

## Current limitation

These salvaged outputs are useful for visual inspection and panel generation.

They are not as clean as a fresh path-fixed rerun.

`amicuse01` is still missing `rendered_normal_t5.png`, so a clean rerun may still be needed later for that case.
