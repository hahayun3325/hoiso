# Phase 0.17 — Saved Output Guide

## Why we save both PNG and PLY

The pipeline now saves two kinds of intermediate outputs.

### Native PNG renderings

These are used for report figures.

They are rendered inside the optimization loop with the same camera, FOV, image size, MoGe coordinate frame, and renderer used by the actual guidance losses.

Use these images when explaining the visual pipeline to a professor.

Important native images:

foho_selector_before_phase42_native.png
foho_selector_phase42_before_joint_native.png
rendered_obj_normal_t*_opt*.png
rendered_normal_t*.png
rendered_normal_hand_t*_opt*.png

Meaning:


foho_selector_before_phase42_native.png:  object candidate before object-only optimizationfoho_selector_phase42_before_joint_native.png:  object candidate after object-only optimization and before joint optimizationrendered_normal_t*.png:  final or intermediate hand-object native renderIn many native render grids:  left image  = rendered mesh normal  right image = MoGe/target normal reference


### PLY meshes

These are used for verification and scoring.

Use PLY files for:


fragmentation scorecomponent countlargest face ratiomd5 identity checkdebugging mesh geometrymetric computation


Important selector PLY files:


selector_candidate_before_phase42.plyselector_candidate_phase42_before_joint_true.plyselector_selected_before_joint.ply


Meaning:


selector_candidate_before_phase42.ply:  object state before Phase 4.2 object-only optimizationselector_candidate_phase42_before_joint_true.ply:  object state after Phase 4.2 and before Phase 4.3 joint optimizationselector_selected_before_joint.ply:  the object state actually passed into Phase 4.3


## How to verify the selector

The selector is verified by three signals:


1. log line:   before_frag=..., current_frag=..., selected=...2. md5:   selected mesh should match the chosen candidate mesh3. native PNG:   selected candidate should be highlighted in the report panel


## Current selector score

The current automatic selector uses fragmentation score:


fragmentation_score = (num_components - 1) + (1 - largest_face_ratio)


Lower is better.

## Current limitation

The selector is geometry-only.

It does not yet use:


object-mask consistencydepth/normal consistencyscale sanitycontact plausibility


These will be future confidence terms in HOLDSE-Flow.  
