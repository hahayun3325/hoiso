# Selector-v4 pipeline integration plan

## Goal
Integrate selector-v4 as a post-candidate verification gate before accepting a generated hand-object result.

## Current validated behavior
Selector-v4 uses:
- unsigned contact distance
- floating flag
- two-direction penetration diagnostics
- object fragmentation
- largest connected component ratio
- object bbox scale

## Dry-run behavior
For each case, selector-v4 can output:
- `select`
- `selected_with_warning`
- `reject_both_or_rerun`

## First integration stage
Run selector-v4 after candidate generation and log the decision only. Do not change the main optimization behavior yet.

## Second integration stage
If one valid candidate exists, choose it.
If all candidates fail, either:
1. rerun object generation with revised prompt,
2. send candidate to contact-aware optimization,
3. mark case as reject/rerun.
