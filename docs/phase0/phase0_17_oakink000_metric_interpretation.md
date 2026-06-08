# Phase 0.17 — OakInk split000 Metric Interpretation

## Compared runs

- Baseline: `oakink000_default_short`
- Method: `oakink000_gpt55_short_selector_auto_frag_v7_truefile`

## Current diagnostic result

The GPT-5.5 prompt plus internal selector improves object completeness:

- baseline object components: 2
- method object components: 1
- baseline fragmentation score: 1.0055
- method fragmentation score: 0.0

However, it does not improve object-GT diagnostic shape metrics or hand-object proximity on split000:

- baseline object-GT CD is lower
- baseline object-GT F-score is higher
- baseline hand-object distance is lower

## Interpretation

The selector is currently effective as an object-completeness safeguard.

It is not yet an alignment/contact improvement module.

## Correct claim

GPT-5.5 prompting plus the internal selector improves object completeness, but a contact-aware refinement stage is still needed to improve pose and hand-object alignment.

## Incorrect claim

Do not claim that GPT-5.5 prompting plus the selector improves object pose/alignment on OakInk split000 yet.
