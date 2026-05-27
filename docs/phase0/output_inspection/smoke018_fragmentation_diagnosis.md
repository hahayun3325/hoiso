# Smoke 018 — Fragmentation Diagnosis

## Main observation

Smoke 018 confirms that the final object is already fragmented in the Hunyuan guidance debug output.

The debug output:

foho_debug/.../final_obj_mesh.ply

is fragmented.

The exported output:

`guidance_out/test_obj.ply`

is also fragmented.

## Component evidence

The Hunyuan initial mesh is complete:

hunyuan_hoi_out/test_hoi_mesh.ply:1 component, watertight

The Hunyuan guidance final debug object is highly fragmented:

`foho_debug/.../final_obj_mesh.ply:105 components, not watertight`

The exported object is still fragmented:

guidance_out/test_obj.ply:6 components, watertight after post-processing

## Interpretation

The final post-processing removes many small floating pieces, but it does not fix the main object fragmentation.

The root is inside the Hunyuan final guidance path, before `guidance_out/test_obj.ply` is exported.

## Next diagnostic

Smoke 019 should export:

- `debug_obj_before_hunyuan2moge.ply`
- `debug_obj_after_hunyuan2moge.ply`
- `debug_obj_after_final_rt_scale.ply`

This will locate whether fragmentation begins in:

- final latent/SDF/FlexiCubes extraction,
- Hunyuan-to-MoGe transform,
- final RT/scale transform.  
