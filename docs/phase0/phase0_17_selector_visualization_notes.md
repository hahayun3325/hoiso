# Phase 0.17 — Selector Visualization Notes

## What is verified

The automatic internal selector is verified by logs and md5 checks.

It compares:

1. `before_phase42`
2. `phase42_before_joint_true`

and exports:

1. `selector_candidate_before_phase42.ply`
2. `selector_candidate_phase42_before_joint_true.ply`
3. `selector_selected_before_joint.ply`

The md5 check confirms that the selected mesh equals the candidate chosen by the selector.

## Current visualization limitation

The selector candidate meshes are saved in an internal optimization coordinate frame.

The final HOI mesh is saved in the final hand-object frame.

The input image is in the 2D camera frame.

Therefore, a simple matplotlib/trimesh rendering can make candidate object poses look twisted or blob-like even when the selector logic is correct.

## Interpretation

The current panel should be used to explain selector decision logic, not exact 2D camera alignment.

For final report figures, we should either:

1. reuse the original pipeline's native rendering functions, or
2. render object candidates in object-local views and final scenes in final-scene-local views with clearer contrast.

## Current conclusion

The selector mechanism is correct. The remaining issue is presentation-quality rendering.
