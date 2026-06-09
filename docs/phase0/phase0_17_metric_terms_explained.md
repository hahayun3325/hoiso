# Phase 0.17 — Metric Terms Explained

## MANO-correspondence paper-like metric

The predicted hand and GT hand are both MANO-topology meshes with 778 vertices.

We align the predicted hand to the GT hand using corresponding MANO vertices. Then we apply the same transform to the predicted object.

This does not move the object into "hand space." Instead, it uses the hand as the alignment anchor and evaluates the object in the GT camera coordinate after hand-based alignment.

## Similarity ICP

Similarity ICP aligns the predicted hand to the GT hand using nearest-neighbor correspondences.

For OakInk split000, similarity ICP produced a degenerate transform with scale 0.0, so it should not be reported.

## Chamfer Distance

Chamfer Distance samples points on the predicted and GT object surfaces and averages nearest-neighbor distances in both directions.

CD can hide collapse because a broken object fragment may still be close to part of the GT object surface.

## F-score

F-score measures how many predicted and GT object points are within a distance threshold, such as 5 mm or 10 mm.

F-score is more sensitive to missing object parts and surface coverage than average CD.

## Fragmentation

Fragmentation measures whether the predicted object mesh is broken into multiple disconnected components.

It directly captures object collapse or broken geometry.

## hand_align_rmse

hand_align_rmse is the RMSE between the aligned predicted hand vertices and GT hand vertices.

It evaluates hand alignment quality. It is not the distance between the hand and object.
