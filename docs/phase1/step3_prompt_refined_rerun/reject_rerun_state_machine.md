# Selector-v4 reject-and-rerun state machine

## Goal

When selector-v4 rejects both object candidates, the pipeline should not force-select the less bad candidate. The old failed prompts are kept as baseline evidence, but the rerun should directly use the refined part-aware prompt.

## Policy

If both original candidates are rejected:

1. record the selector-v4 rejection reason;
2. assign the part-aware refined prompt;
3. rerun object inpainting, object reconstruction, and object pose optimization;
4. run selector-v4 again;
5. if the rerun passes, accept it;
6. if the rerun fails, reinpaint once with the refined prompt or a failure-specific refined variant;
7. rerun object reconstruction and pose optimization;
8. run selector-v4 again;
9. if it still fails, mark the case as `failed_after_reinpaint`.

## States

1. `old_candidates_rejected`
2. `partaware_prompt_assigned`
3. `prompt_refined_attempt0_running`
4. `selector_v4_recheck_attempt0`
5. `accepted_after_prompt_refined_rerun`
6. `reinpaint_attempt1_running`
7. `selector_v4_recheck_attempt1`
8. `accepted_after_reinpaint`
9. `failed_after_reinpaint`

## Failure-specific refinement

- `severe_floating`: emphasize object scale, visible silhouette, and contact-facing surfaces.
- `severe_penetration`: emphasize part layout, physical thickness, and negative shape constraints.
- `severe_fragmentation`: emphasize one coherent connected object.
- `low_integrity`: emphasize main body, parts, and visible geometry.
- `oversized_object`: emphasize true object scale and what the object is not.

## ARCTIC rerun policy

For ARCTIC, directly use the part-aware v2 prompts for rejected cases. Do not repeat the old failed GPT-5.5 prompts unless needed for ablation.
