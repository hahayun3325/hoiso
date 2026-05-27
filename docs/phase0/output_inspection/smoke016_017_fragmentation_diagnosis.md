# Smoke 016 / 017 — Final Object Fragmentation Diagnosis

## Main observation

The structured prompt successfully improves the inpainted object and the Hunyuan initial mesh.

However, the final object meshes from smoke_016 and smoke_017 are fragmented.

## Evidence

Connected-component analysis shows:

smoke_013 final object: 1 connected component
smoke_016 final object: 6 connected components
smoke_017 final object: 4 connected components

This means the final object fragmentation is real, not only a rendering artifact.

## Important comparison

The smoke_015 Hunyuan initial mesh is complete and preserves the boxy SPAM shape.

The smoke_017 final object is incomplete, even though it uses the same smoke_015 intermediate outputs and increases final octree resolution from 128 to 192.

## Interpretation

The degradation is not caused by final octree resolution alone.

The likely cause is inside the final guidance / object extraction stage, such as:

- object SDF fragmentation during guidance,
- hand-object separation damaging object geometry,
- mask/normal/silhouette constraints preserving only partial visible regions,
- low guidance steps causing unstable object geometry,
- post-processing exporting disconnected object islands.

## Research implication

This supports the HOLDSE-Flow motivation:

A pipeline can have good semantic prompting and good initial 3D generation, but later optimization can still damage object geometry.

Therefore, the system needs:

- stage-wise confidence checking,
- 2D-3D semantic consistency verification,
- object completeness verification,
- contact-aware but geometry-preserving optimization,
- confidence-guided coordination between semantic, geometric, and physical constraints.  
