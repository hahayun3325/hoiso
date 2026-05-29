# Phase 0.16 — Official Evaluation Script Inspection

## Goal

Understand how FollowMyHold evaluates outputs before running more data.

## Current status

The optional object fallback module has been added as a post-processing switch and is default-off.

This allows clean comparison between:

- original FollowMyHold output,
- prompt-improved output,
- fallback-enabled output.

## Test splits found

The repository contains official-style test split files:

- `test_splits/dexycb_test.csv`
- `test_splits/arctic_test.csv`
- `test_splits/oakink_test.csv`

## Initial observation

The first inspection found dataset split files and many generic metric/evaluation utilities, but the exact official FollowMyHold metric script still needs to be located or reconstructed.

## Next questions

1. Where are CD / F5 / F10 computed?
2. Where is intersection volume computed?
3. How is reconstruction rate computed?
4. What output folder format does evaluation expect?
5. Does the repository include official evaluation code, or do we need to reimplement it from the paper/supplement?
