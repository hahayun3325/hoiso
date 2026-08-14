# HOISO-Flow pipeline, story, abstract, and optimization plan

Updated: 2026-08-14 (America/Chicago)

## Story

HOISO-Flow treats foundation-model predictions as fallible evidence, contains
upstream errors before they propagate, preserves articulated object parts, and
compiles coarse contact semantics into verified geometric constraints.

## Pipeline

Foundation evidence -> Auto-v2 evidence containment -> Gate-A part-aware object
-> Gate-B coarse contact -> Gate-C shared MoGe initialization -> D0 compiler
-> hand refinement -> object zero audit/optional refinement -> bounded joint
refinement -> independent D1.

Current transform endpoints are Gate-A `G -> I` for the object and HaMeR
`H -> Uhoi -> I` plus bounded CPU refinement for the hand. Both meet in the
same hash-owned MoGe frame `I`.

## CPU-to-optimization transition

The global CPU search is complete as initializer generation. Step 5 remains a
diagnostic initializer, not a passed scientific or live zero. Before any
updates, D0 must be compiled, dense valid object z-order must replace sparse
sentinel supervision, and an exact zero-update live replay must pass.

## Gate B, D0, and D1

Gate B proposes semantic contact. Binding proves its provenance. D0 asks only
for missing semantic specificity and deterministically maps it to current MANO
and Gate-A geometry. D1 independently verifies the final result and cannot be
passed by the same VLM output alone.

## Experiment order

1. Complete D0 and the dense valid z-order owner.
2. Run capture-only live zero.
3. Run at most five D0-selected finger/palm updates with object, global hand
   transform, scale, shape, and unselected articulation frozen.
4. Audit Gate-A seed 2026; skip object updates if it remains valid.
5. If necessary, run at most five object-only updates with the hand frozen.
6. Run a short D0-guided joint trust region.
7. Run independent D1 and preserve rollback throughout.

## Abstract draft

Monocular reconstruction of hand-articulated-object interactions commonly
combines foundation models whose outputs differ in geometry, scale, coordinate
frame, and semantic reliability. A locally plausible upstream error can
therefore propagate into physically invalid hand-object alignment. We propose
HOISO-Flow, a verification-gated reconstruction pipeline that treats
foundation-model predictions as evidence rather than unquestioned state. The
pipeline uses branch-local evidence adjudication to contain upstream failures,
a part-aware object stage to preserve articulated structure, and hash-owned
coordinate contracts to initialize trusted object and hand assets in a shared
MoGe frame. Staged refinement is governed by an explicit semantic-to-geometric
contact contract: Gate B proposes coarse contact semantics, Gate D0 maps them
to selected MANO fingers and localized allowed object-part surfaces while
specifying forbidden contact and occlusion constraints, and Gate D1
independently validates the resulting interaction. The method combines image,
depth, contact, and collision evidence under hard non-regression gates so that
a lower scalar loss cannot silently replace a physically valid intermediate
state. The design targets containment of upstream errors, part-aware
articulated-object ownership, and verified contact-aware refinement. We will
evaluate reconstruction accuracy, contact localization, penetration, failure
containment, wall-clock time, and peak GPU memory under matched baselines.
Efficiency and alignment superiority remain empirical questions rather than
assumed claims.
