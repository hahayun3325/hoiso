# Phase 0.17 — ARCTIC Panel Interpretation

## Current ARCTIC panel

The ARCTIC panel uses native pipeline render images where available.

The panel columns are:

1. input
2. crop
3. inpaint
4. before Phase 4.2
5. after Phase 4.2
6. final HOI native render

## Important limitation

The current before/after Phase 4.2 images are fallback native optimization renders.

They are not pure object-only selector-candidate renders.

This means they may include both hand and object because the pipeline renderer visualizes the HOI optimization state and MoGe target geometry.

## Fallback rule

If selector-native images are missing, the panel uses:

before Phase 4.2  -> rendered_obj_normal_t3_opt0.png
after Phase 4.2   -> rendered_normal_t4.png
final HOI render  -> rendered_normal_t5.png
if t5 missing     -> rendered_normal_t4.png

## Current status

The salvaged ARCTIC runs are useful for qualitative inspection.

For a clean report figure, only `amicuse01` may need a rerun because `rendered_normal_t5.png` is missing.
