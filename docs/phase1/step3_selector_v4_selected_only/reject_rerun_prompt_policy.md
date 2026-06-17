# Reject-and-rerun prompt policy

## Motivation

Selector-v4 can reject both object candidates when neither candidate has plausible hand-object relation or object integrity. In this case, the pipeline should not force-select the less bad candidate.

## Policy

If both candidates are rejected:

1. record the rejection reason;
2. generate a refined object prompt;
3. rerun object inpainting and object reconstruction;
4. rerun object pose optimization;
5. run selector-v4 again.

## Failure-specific prompt update

- `severe_floating`: emphasize object scale, contact-facing surfaces, and visible silhouette.
- `severe_penetration`: emphasize part layout, object thickness, and negative constraints.
- `severe_fragmentation`: emphasize one coherent main body and connected parts.
- `low_integrity`: emphasize object category, part relation, and visible geometry.
- `oversized_object`: emphasize true object scale and negative shape constraints.

## ARCTIC articulated objects

For articulated objects such as scissors, laptop, and microwave, prompts should include:
- rigid/articulated type;
- main parts;
- hinge or pivot relation;
- open/closed state;
- thin/flat/contact-relevant surfaces;
- negative constraints.
