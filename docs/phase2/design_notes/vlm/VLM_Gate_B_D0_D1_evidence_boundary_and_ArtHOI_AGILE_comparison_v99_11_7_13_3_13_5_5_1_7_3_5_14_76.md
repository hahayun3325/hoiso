# VLM Gate B/D0/D1 evidence boundary and relation to ArtHOI/AGILE

Generated: 2026-08-16T17:48:53.533150+00:00

## Scope

This note freezes the current single-image VLM design and its non-claims. It
separates semantic inference from geometry compilation, optimization, and final
validation. It is based on the project's local ArtHOI and AGILE papers.

## Gate roles

| Gate | Primary question | Output | Prohibited authority |
|---|---|---|---|
| B | Which hand and articulated-object parts/relationships are visible or plausible? | broad symbolic parts, active hand, uncertainty and coarse interaction hypotheses | mesh IDs, metric transforms, loss weights, optimizer authorization |
| D0 | Which named fingers/palm region should contact which named object region, and what must remain clear? | pre-optimization contact, forbidden-contact and z-order hypotheses | direct geometry movement, metric depth/scale, collision certification |
| D1 | Did the reconstructed result realize the intended interaction without floating, wrong contact, or penetration? | pass/review/reject and failure reasons | silent repair, GT access, or optimizer updates |

Gate A owns object-part geometry. Gate B is a broad independent semantic
proposal/check. D0 is the pre-optimization contract. The compiler resolves
semantic names to predicted MANO/Gate-A IDs; the adapter chooses live losses and
movable parameter groups. D1 is a post-optimization jury and must see the
original observation plus pipeline-generated final diagnostics.

## Current input boundary

Gate B and D0 each receive one standardized original crop and one frozen,
role-specific prompt. The original crop is primary because arm continuity, the
other hand, support context and viewpoint help infer the active hand, palm
direction and likely motion under occlusion. A canonical foreground crop that
removes the arm is retained only as an ablation.

## Relation to ArtHOI

ArtHOI uses an MLLM for frame-wise contact state and contacting-finger
reasoning. It first reasons about camera perspective/laterality and concatenates
neighboring RGB frames with colorized predicted depth maps to reduce
contact-versus-proximity false positives. Its semantic contact output becomes a
constraint in hand-object alignment. This is richer evidence than our present
single-crop query and should be treated as a future ablation, not claimed as
equivalent.

## Relation to AGILE

AGILE's VLM primarily selects informative video keyframes and critiques
generated multiview images and refined assets during rejection sampling. Its
contact-aware tracking then uses joint reprojection, masks, semantic features,
SDF-weighted interaction stability and nonpenetration. Thus AGILE's VLM is a
generative-quality supervisor; it is not simply a D0 finger-to-part compiler.

## Benefits and limitations of single-crop querying

Benefits:

- available at ingestion before masks, depth and reconstruction exist;
- lower visual-token, latency and orchestration cost than multi-frame/depth prompts;
- less circular dependence on fallible upstream predicted modalities;
- a small, auditable evidence boundary suited to manual collection now and API automation later;
- independent Gate B/D0 answers can be compared instead of one answer priming the other.

Limitations:

- weaker evidence under occlusion, laterality ambiguity and near-contact;
- symbolic guidance cannot supply metric placement or certify collision;
- no claim of superior accuracy, total memory or generalization is warranted without measurement;
- D1 cannot judge the final 3D result from the raw crop alone.

## Ground-truth-free and anti-leakage contract

1. The VLM-visible Gate B/D0 payload is only the deterministic crop plus frozen prompt.
2. Never expose dataset/case/file names, object category, annotations, GT geometry/pose/depth/contact, evaluation scores, receipts, hashes or prior gate answers.
3. Cropping and retry policy are category-independent and frozen across cases.
4. Preserve raw Gate B and D0 JSON; do not semantically hand-edit answers.
5. Compiler maps use only pipeline-predicted MANO and Gate-A artifacts.
6. D1 may use the observation and pipeline-generated diagnostics, never GT or evaluator output.
7. Ground truth is loaded only by an offline evaluator after pipeline decisions are frozen.
8. Prompts, thresholds and optimizer weights are not tuned from per-case GT outcomes.

Hiding the category alone is insufficient: GT-derived crops, GT-selected
frames, per-case GT tuning, or GT-informed human corrections are also leakage.

## Future multimodal ablation

After completing the RGB-only system, compare: original RGB; RGB plus predicted
masks; RGB plus predicted depth; and neighboring RGB frames plus predicted
depth. Keep schemas and downstream optimization fixed. Report query cost,
latency, memory, contact accuracy/false positives and final reconstruction
success. All auxiliary evidence must be prediction-derived and unavailable
when its validity checks fail.
