# Phase 0.17 — OakInk split000 Paper-Like Metric Result

## Compared runs

- Baseline: `oakink000_default_short`
- Method: `oakink000_gpt55_short_selector_auto_frag_v7_truefile`

## Valid metric

The main valid result is the MANO-correspondence hand alignment result.

Because both predicted and GT hands are MANO-style meshes with 778 vertices, vertex correspondence is a reasonable one-sample alignment method.

## Result

The GPT-5.5 + selector run improves object reconstruction compared with the baseline:

- CD: 75.63 mm -> 75.24 mm
- F5: 0.00055 -> 0.03769
- F10: 0.00521 -> 0.07370
- object components: 2 -> 1
- fragmentation: 1.0055 -> 0.0

## Interpretation

The improvement is strongest in F-score and fragmentation, which better reflect object completeness.

The CD improvement is small because Chamfer distance can hide object collapse when a broken fragment remains close to part of the GT object.

## Invalid robustness result

The similarity-ICP run is not reliable because it collapsed to `sim_scale=0.0` and produced identical CD for both methods. This is a degenerate transform and should not be reported.

## Current claim

GPT-5.5 prompting plus selector improves object reconstruction/completeness on OakInk split000.

## Current limitation

The method still does not fully solve hand-object contact/alignment. A contact-aware refinement module is still needed.
