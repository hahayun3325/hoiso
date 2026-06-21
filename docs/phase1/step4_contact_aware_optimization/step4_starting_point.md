# Step 4 starting point: contact-aware optimization

## Input

Use the selector-v4.1 soft-selected outputs as initialization:

`/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_soft_selected_outputs`

## Target manifests

- `arctic5_contact_optimization_targets.csv`
- `arctic5_targets_penetration_refinement.csv`
- `arctic5_targets_contact_repose.csv`

## Goal

Improve hand-object physical relation after selector-v4.1 chooses the most coherent candidate.

## Main target types

1. penetration resolution and contact refinement
2. contact attraction and object pose repositioning

## Important note

The soft-selected outputs are not final physical reconstructions. They are initialization for contact-aware optimization.
