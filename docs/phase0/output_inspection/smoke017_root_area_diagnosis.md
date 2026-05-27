# Smoke 017 — Root Area Diagnosis for Fragmented Object Mesh

## Main finding

The final object mesh is already fragmented in the debug output:

foho_debug/.../final_obj_mesh.ply

The exported output:

guidance_out/test_obj.ply

is also fragmented.

## Interpretation

This means the fragmentation is not mainly caused by the final `src/foho/guidance/run.py` post-processing stage.

The object is already damaged before `guidance_out/test_obj.ply` is saved.

## Current root area

The likely root is inside the Hunyuan guidance pipeline, around the creation of:

debug_transformed_obj_mesh

This mesh is created from final object vertices/faces, then transformed into the MoGe / final coordinate space.

## Likely causes

- guidance-time object SDF becomes fragmented
- final object extraction from the guided latent/SDF is unstable
- hand-object separation damages the object
- object normal/silhouette guidance only preserves partial visible regions
- low guidance steps produce unstable object geometry
- final transform/export preserves already-fragmented geometry

## Important conclusion

Structured prompting fixes the earlier semantic drift, but later guidance can still destroy object completeness.

This supports the need for:

- stage-wise confidence checks
- object completeness verification
- 2D-3D consistency checking
- confidence-guided object source selection
- geometry-preserving contact refinement  
