# Selector-v4 reject-and-rerun state machine

## Goal

When selector-v4 rejects both object candidates, the pipeline should not force-select the less bad candidate. Instead, it should record the failure reason and trigger a prompt-refined rerun.

## State machine

1. `candidate_generated`
   - default and selector/GPT candidates exist.

2. `selector_v4_checked`
   - contact distance, floating, penetration, object integrity, and scale are computed.

3. `selected`
   - at least one candidate passes the hard gates.
   - selected-output-only mode copies the accepted result to the final selected folder.

4. `reject_both_or_rerun`
   - both candidates fail.
   - rejection reason is stored.

5. `prompt_refined`
   - a new part-aware prompt is assigned based on the failure reason.

6. `rerun_object_generation`
   - rerun object inpainting and object reconstruction.

7. `rerun_pose_optimization`
   - rerun object pose optimization.

8. `selector_v4_recheck`
   - rerun selector-v4 on the new result.

9. `accepted_after_rerun` or `failed_after_rerun`
   - if the rerun passes, accept it.
   - if it still fails, save diagnostics and do not force-select.

## Failure-specific prompt refinement

- `severe_floating`: emphasize object scale, visible silhouette, and contact-facing surfaces.
- `severe_penetration`: emphasize part layout, physical thickness, and negative shape constraints.
- `severe_fragmentation`: emphasize one coherent connected object.
- `low_integrity`: emphasize main body, parts, and visible geometry.
- `oversized_object`: emphasize true object scale and what the object is not.
