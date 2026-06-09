# Phase 0.17 — ARCTIC Paper-Like Evaluation Next Step

## Goal

Extend the OakInk split000 paper-like evaluation to the selected ARCTIC cases.

## Important difference from OakInk

ARCTIC contains both rigid and articulated objects.

For rigid-like cases, such as box or ketchup, the GT object mesh/pose should be easier to resolve.

For articulated cases, such as scissors, laptop, and microwave, the evaluator must handle object parts and articulation state.

## Recommended order

1. Build an ARCTIC manifest for the selected five cases.
2. Locate GT image, GT hand, GT object mesh, object pose, and camera for one simple case.
3. Validate GT overlay visually.
4. Check that baseline and GPT-5.5+selector prediction pairs exist.
5. Run one-case paper-like metrics.
6. Extend to all five cases only after the one-case evaluator is validated.

## First target

Start with either:

- `aket01` ketchup bottle, or
- `abox01` box

Do not start with `amicuse01`, because it is memory-sensitive and articulated/part-structured.
