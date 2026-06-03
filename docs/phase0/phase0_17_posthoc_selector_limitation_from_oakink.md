# Phase 0.17 — Post-hoc Selector Limitation from OakInk split000

## Observation

The selected-object-only panel shows that some selected outputs still contain hand-like geometry.

This happens when the selector chooses `initial_obj`.

## Root cause

The current `initial_obj` is the Hunyuan HOI mesh.

It is not guaranteed to be a clean object-only mesh.

It can contain:

- object geometry,
- hand-like geometry,
- small disconnected components.

Therefore, selecting the full Hunyuan HOI mesh as the object candidate can introduce extra non-object geometry.

## What the selector currently solves

The current selector answers:

Which candidate has better object completeness?

# request

It uses scores such as:

- connected components,
- largest-face ratio,
- fragmentation score.

## What the selector does not solve yet

The current post-hoc selector does not guarantee:

- clean object-only geometry,
- correct hand-object alignment,
- correct front/back relationship,
- contact correctness.

## Design correction

The selector should not be applied as a final post-hoc scene replacement.

Instead, it should be inserted between object-focused refinement and alignment:


Phase 4.2 object-focused refinement→ object-only candidate extraction→ object selector→ Phase 4.3 contact-aware alignment refinement


## Main lesson

The post-hoc selector is useful as a diagnostic tool.

The real pipeline selector should choose an object-only candidate before final alignment.  
