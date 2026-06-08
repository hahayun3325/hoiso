# Phase 0.17 — Contact / Alignment Observation

## Observation

The GPT-5.5 prompt plus selector improves object completeness, but the current diagnostic contact metrics show worse hand-object proximity than the baseline on OakInk split000.

## Interpretation

The selector is currently an object-completeness selector.

It is not yet a contact-aware selector.

The joint optimization phase can adjust hand and object together, but it is not enough to guarantee correct physical contact because it does not use verified part-level contact supervision.

## Why this matters

This supports the next HOLDSE-Flow module:

- use MLLM / geometry to identify likely contact fingers and object regions
- verify contact with 2D/3D consistency
- refine object SE(3) and hand pose using contact-aware losses
- keep global object geometry protected

## Current safe claim

Prompting plus selector improves object-state selection and object completeness.

## Current unsafe claim

Do not claim it improves object pose/contact/alignment until contact-aware refinement and official hand-aligned metrics are added.
