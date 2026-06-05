# Phase 0.17 — Internal Selector Status

## Current status

The internal selector is now inserted between object-only optimization and joint hand-object alignment.

Object-only optimization
→ automatic internal selector
→ joint hand-object alignment
## Evidence from GPT-5.5 OakInk split000

The automatic selector saved and scored two real object states:


[FOHO_INTERNAL_SELECTOR_AUTO] saved before_phase42 mesh at step 3; frag=23.023389, comp=24[FOHO_INTERNAL_SELECTOR_AUTO] before_frag=23.023389, current_frag=28.027992, margin=0.000000, selected=before_phase42[FOHO_INTERNAL_SELECTOR] selected=before_phase42; applied before joint step 4Joint optimization step 4


This proves that the selected object state is passed into Phase 4.3.

## Automatic decision rule

The current automatic selector uses fragmentation score:


fragmentation_score = (num_components - 1) + (1 - largest_face_ratio)


Lower is better.

## Current limitation

This is still a geometry-only selector.

It does not yet use:

- object-mask consistency
- depth/normal consistency
- object scale sanity
- hand-object contact plausibility

## Interpretation

The selector is now internal and automatic, but it is still a first-version confidence module.  
