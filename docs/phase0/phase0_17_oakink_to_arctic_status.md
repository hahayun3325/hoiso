# Phase 0.17 — OakInk to ARCTIC Status

## OakInk split000 result

The native-render LLM comparison panel is now usable.

It includes:

- cropped input
- inpainted object
- object before Phase 4.2
- object after Phase 4.2
- final HOI mesh

The panel uses native pipeline renderings instead of custom matplotlib PLY rendering. This avoids the earlier camera and coordinate mismatch.

## LLM choice

For the next official-dataset proof runs, we choose GPT-5.5 as the default prompt generator.

Reason:

- GPT-5.5 gives strong object inpainting quality on OakInk split000.
- GPT-5.5-thinking is also good, but not clearly better enough for the extra cost.
- GPT-5.5 gives the best current cost-quality tradeoff.

This is a working choice, not a final global conclusion.

## Next dataset

Proceed to ARCTIC with five selected cases:

- `abox01`
- `aket01`
- `ascis01`
- `alapuse01`
- `amicuse01`

## Protocol

Run one ARCTIC proof case first:

- `arctic_abox01_gpt55_auto`

If it passes, run the remaining selected cases.

## Verification

For each run, verify:

- no missing file errors
- no CUDA OOM
- no selector fallback like `before_frag=999`
- selector decision is printed
- final object/hand/HOI outputs exist
