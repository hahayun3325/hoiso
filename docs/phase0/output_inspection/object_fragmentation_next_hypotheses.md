# Object Fragmentation — Next Hypotheses

## Current evidence

The structured prompt creates a good inpainted object and a good Hunyuan initial HOI mesh.
The final smoke_016 and smoke_017 object meshes become fragmented.

## Most likely location of failure

The failure likely happens during final guidance / object extraction, not during inpainting or initial Hunyuan generation.

## Hypotheses to test

1. Final object SDF becomes fragmented during guidance.
2. Object extraction / hand-object separation damages the object.
3. Mask/normal/silhouette guidance preserves only partial visible object regions.
4. Low guidance steps cause the object to collapse into partial surfaces.
5. Final post-processing exports multiple disconnected object islands.
6. The Hunyuan initial HOI mesh may be better for object shape than the final object mesh.

## Proposed diagnostic

Use the Hunyuan initial mesh as an object-shape fallback when final object completeness is low.

This motivates a confidence-guided object source selector:

- if final object has many disconnected components, low completeness, or poor silhouette agreement,
- fallback to initial Hunyuan object shape or rerun guidance with stronger object-preservation constraints.
