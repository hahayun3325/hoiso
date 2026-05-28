# HOLDSE-Flow Design Lessons from Object Fragmentation

## Main lesson

A later output is not always better.

In the SPAM case, structured prompting gives a good inpainted object and a good Hunyuan initial mesh. However, final guidance fragments the object.

## Design principle

Object geometry should be stable.  
Hand/contact alignment should be flexible.

## Recommended HOLDSE-Flow structure

1. Generate multiple object candidates.
2. Score each candidate using object completeness and 2D–3D consistency.
3. Select the best object source.
4. Freeze or strongly regularize object shape.
5. Optimize only object pose, hand pose, and verified contact.
6. Reject final results if object completeness gets worse.

## Why this matters

This turns the pipeline from blind sequential processing into confidence-guided coordination.

## Related-work inspiration

- ArtHOI: use structured MLLM contact reasoning and apply contact constraints to verified contacting fingers.
- ForeHOI: connect 2D object completion and 3D shape completion instead of letting them drift independently.
- WHOLE: use contact/mask constraints, but coordinate them with trajectory and consistency terms.
