# selector-v4.1 full-pipeline integration plan

## Goal

Rerun selector-v4.1 inside the pipeline using the refined prompt template and evaluate the final HOI mesh.

## Comparison groups

1. baseline
2. selector + GPT-5.5
3. selector-v4.1 + refined prompt template

## Cases

ARCTIC:

- `abox01`
- `aket01`
- `ascis01`
- `alapuse01`
- `amicuse01`

Optional OAKInk:

- `oakink_split000`

## Evaluation

Evaluate final HOI meshes with:

1. GT reconstruction metrics: CD, F5, F10
2. physical metrics: contact distance, floating, penetration, object integrity
3. hand-object relative-pose metrics: relative object center error after hand alignment

## Interpretation

Selector-v4.1 should be judged by the final HOI mesh after joint optimization, not only by the soft-selected intermediate mesh.
