# Phase 0.16 — Evaluation Reimplementation Plan

## Goal

Reconstruct the official FollowMyHold evaluation as closely as possible.

## Metrics

### Reconstruction Rate

R.R. = number_of_successful_outputs / number_of_test_samples

A sample is successful if required output files exist and are readable.

### Hand-aligned object metrics

1. Load predicted hand and object.
2. Load ground-truth hand and object.
3. Align predicted hand to ground-truth hand using similarity ICP.
4. Apply the same transform to predicted object.
5. Sample 30K points from predicted object and ground-truth object.
6. Compute CD, F5, and F10.

### Intersection Volume

Use trimesh to voxelize hand-object intersection with voxel size 0.5cm.

## Outputs expected per sample

A first simple format:

results/<dataset>/<img_id>/  test_hand.ply  test_obj.ply  fallback_out/selected_hand.ply  fallback_out/selected_obj.ply  fallback_out/fallback_report.json

## First implementation target

Start with one DexYCB or HO3D sample because YCB object meshes are easier to locate and verify.

Then extend to OakInk and ARCTIC.  
