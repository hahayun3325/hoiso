# Object Source Fallback Design

## Motivation

The structured prompt creates a good Hunyuan initial object, but final guidance can fragment the object mesh.

Therefore, the pipeline should not always trust the final-stage object.

## Rule

Compute object completeness score for each candidate:

- Hunyuan initial object / HOI mesh
- final guided object
- post-processed final object

If the final guided object has high fragmentation score, fallback to the earlier object source.

## Initial decision rule

if final_object.components > 2 or fragmentation_score > 1.5:
    reject final object
    use earlier-stage object source
else:
    use final object

## Research meaning

This is confidence-guided coordination:

- use semantic/generative model for object shape,
- use guidance for hand/contact alignment,
- reject later outputs when they damage object completeness.  
