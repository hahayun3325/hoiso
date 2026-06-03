# Phase 0.17 — Selector Insertion Code Notes

## Current outer guidance boundary

The outer wrapper is:

src/foho/guidance/run.py
It calls:


obj_mesh, hand_mesh = pipeline(...)


and then exports:


guidance_out/<index>_obj.plyguidance_out/<index>_hand.ply


This is too late for the correct selector design.

## Current Hunyuan initial export

The Hunyuan initial HOI mesh is exported in:


src/foho/geometry/hunyuan.py


as:


<index>_hoi_mesh.ply


This mesh may contain both object-like and hand-like components, so it should not be blindly used as an object-only candidate.

## Correct internal selector location

The real selector should be inserted inside:


third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py


The target region is:


object refinement startsobj_latent_x1 = self.scheduler.step_final(...)obj_pred_sdf = latent2sdf(...)obj_mesh = Meshes(...)moge_obj_mesh = transform_hunyuan2moge(...)transformed_obj_mesh = transform_mesh_around_center_w_scale(...)


The selector should run after `transformed_obj_mesh` is created and before the joint hand-object alignment block begins.

## Current debug-export result

The debug hook successfully exports internal object candidates before the joint optimization block.

For `oakink000_gpt54thinking_short`, these candidates have high fragmentation:


components = 23fragmentation_score = 22.2516


This means the object can already be broken before the joint alignment block.

## Design implication

The selector should not simply trust the current Phase 4.2 object.

It should compare:

1. trusted earlier object candidates,
2. current object-focused refinement candidate,
3. optional prompt/inpaint alternatives.

## Correct design


Object-focused refinement→ export/score object-only candidates→ selector chooses reliable object geometry + pose→ joint hand-object alignment uses the selected object


## What Phase 4.3 should do

Phase 4.3 should refine hand-object alignment.

It should not globally deform the selected object.

It should optimize mainly:

- object SE(3),
- hand global pose,
- local contact vertices.  
