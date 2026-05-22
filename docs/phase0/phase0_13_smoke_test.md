# Phase 0.13 — First Smoke Test

## Goal

Run the first FollowMyHold smoke test using one HO3D image.

## Input

`~/foho_phase0/inputs/test_hoi_ho3d_ShSu13_0005.png`

## Output folder

`~/foho_phase0/runs/smoke_001`

## Command

PYTHONPATH=src python3 -m foho.main --config configs/pipeline.phase0.env

## Evaluation

The smoke test should be judged by:

- Whether the pipeline completes without crashing.
- Whether intermediate outputs are created.
- Whether masks, hand outputs, object/HOI mesh outputs, and guidance/debug outputs exist.
- If it fails, which stage fails first.

## Decision

Record result after inspecting logs and artifacts.  
