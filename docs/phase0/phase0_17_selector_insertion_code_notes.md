# Phase 0.17 — Selector Insertion Code Notes

## Current code search result

The final guidance output is exported in:

src/foho/guidance/run.py

Important lines found by grep:


obj_mesh.export(save_path_obj)save_path_obj = os.path.join(guidance_out_dir, f"{index}_obj.ply")save_path_hand = os.path.join(guidance_out_dir, f"{index}_hand.ply")


The Hunyuan initial HOI mesh is exported in:

src/foho/geometry/hunyuan.py

as:

{i}_hoi_mesh.ply


## Meaning

The current visible hook is at the outer boundary:


guidance pipeline returns obj_mesh, hand_mesh→ run.py exports final object and hand


This is too late for the desired selector design.

## Correct design

The selector should run inside the guidance pipeline, after object-focused refinement and before final joint hand-object alignment.

## Required engineering step

Expose intermediate object candidates from inside the guidance pipeline:

1. object before object-focused refinement,
2. object after object-focused refinement,
3. object before final joint alignment,
4. object after final alignment.

Then run selector on object-only candidates before final alignment.

## Temporary diagnostic implementation

Use scripts to:

1. split Hunyuan HOI mesh into connected components,
2. inspect whether components are object-like or hand-like,
3. select from object-only candidates,
4. avoid using the full Hunyuan HOI mesh as an object candidate.  
