# Phase 0.17 — Internal Selector Variant Result

## Goal

Test whether the internal selector hook can pass a chosen object state into Phase 4.3.

## Compared variants

1. `phase42_before_joint`
   - use the object state after Phase 4.2 object optimization

2. `before_phase42`
   - restore the object state saved before Phase 4.2 object optimization

3. `auto_fragmentation`
   - automatically choose the candidate with lower fragmentation score

## Evidence from logs

The selector hook runs between object optimization and joint alignment:

[FOHO_INTERNAL_SELECTOR] saved before_phase42 state at step 3
Object optimization step 3
[FOHO_INTERNAL_SELECTOR] selected=phase42_before_joint; applied before joint step 4
Joint optimization step 4
## Manual selector result

The Phase 4.2 object state is much cleaner than the state before Phase 4.2:


phase42_before_joint: fewer components, lower fragmentationbefore_phase42: many components, high fragmentation


Observed GPT-5.5 example:


phase42_before_joint: components = 2, fragmentation_score = 1.0011before_phase42: components = 21, fragmentation_score = 20.0333


## Current interpretation

The selector hook is functional and located at the correct stage.

Before the automatic patch, the selected state was controlled manually by:


FOHO_INTERNAL_PHASE42_SELECTOR_CHOICE=phase42_before_joint


or:


FOHO_INTERNAL_PHASE42_SELECTOR_CHOICE=before_phase42


## Automatic selector goal

The next version uses:


FOHO_INTERNAL_PHASE42_SELECTOR_CHOICE=auto_fragmentation


and automatically chooses the lower-fragmentation object state.

## Next step

After verifying `auto_fragmentation` on GPT-5.5, rerun all LLM prompt comparisons with the same automatic selector setting.  
