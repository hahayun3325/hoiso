# Phase 0.17 — Internal Selector Variant Result

## Goal

Test whether the internal selector hook can pass a chosen object state into Phase 4.3.

## Compared variants

1. `phase42_before_joint`
   - use the object state after Phase 4.2 object optimization

2. `before_phase42`
   - restore the object state saved before Phase 4.2 object optimization

## Evidence from logs

The selector hook runs between object optimization and joint alignment:

[FOHO_INTERNAL_SELECTOR] saved before_phase42 state at step 3
Object optimization step 3
[FOHO_INTERNAL_SELECTOR] selected=phase42_before_joint; applied before joint step 4
Joint optimization step 4

This proves the selector is placed at the correct stage.

## Result

The Phase 4.2 object state is much cleaner than the state before Phase 4.2.

Observed pattern:


phase42_before_joint: fewer components, lower fragmentationbefore_phase42: many components, high fragmentation


## Interpretation

The current selector hook is functional, but not fully automatic.

It can pass a selected object state into Phase 4.3, but the selected state is still controlled by an environment variable.

## Next step

Replace manual selection with automatic scoring.

Recommended first decision rule:


choose the candidate with the lower fragmentation score


Later add:

- 2D object mask consistency
- depth consistency
- normal consistency
- hand-object contact plausibility  
