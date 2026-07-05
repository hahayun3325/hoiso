# alapuse02_v3b mask repair v1 final decision

## Decision

PASS_MASK_REPAIR

## What changed

The segmentation prompt was separated from the long reconstruction prompt.

Instead of using the full geometry-rich reconstruction prompt, the segmentation
stage used:

open toy laptop screen keyboard

via:

FOHO_SEGMENT_OBJECT_PROMPT

## Observation

The new cropped object mask covers the laptop screen / hinge / keyboard-base
region instead of the support box/table.

## Interpretation

The original alapuse02_v3 failure was not caused by MoGe, Hunyuan, or the
optimizer. It was caused by upstream object-mask mis-segmentation.

## Lesson

Different foundation models need different prompts:

- FLUX / Hunyuan / reconstruction: long geometry-rich prompt is useful.
- SAM2 / LangSAM segmentation: short direct phrase works better.

## Next

Proceed to shared-frame dry-run for alapuse02_v3b.
Do not run Gate A until shared-frame hand-object alignment is visually checked.
