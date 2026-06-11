# Phase 0.17 — ARCTIC Surface-Sampled Paper-Style Evaluation Plan

## Current dry-run result

The all-case dry run over five selected ARCTIC samples succeeded.

The selector improves mean object CD from about 98.03 mm to 77.04 mm and slightly improves F5/F10, but the per-case behavior is mixed.

## Difference from final selected-case paper-style metric

The dry run uses raw mesh vertices. This is useful for sanity checking, but it can be biased by mesh tessellation.

The surface-sampled evaluator samples points uniformly from object surfaces and computes:

- Chamfer Distance
- F-score@5mm
- F-score@10mm

## Decision

Proceed to the stricter surface-sampled evaluator.

This should be described as:

`selected-case ARCTIC paper-style evaluation`

not:

`official full ARCTIC benchmark evaluation`

because Phase 0.17 uses five manually selected samples.
