# Phase 0.17 — Hunyuan Component Interpretation  
  
## What the component ranks mean  
  
The Hunyuan mesh was split into connected components.  
  
The ranks are based on face count:  

rank 0 = largest connected component  
rank 1 = second largest connected component  
rank 2 = third largest connected component

The ranks are not semantic labels.

They do not automatically mean:


rank 0 = object
rank 1 = hand
rank 2 = trigger


## OakInk split000 example

For `oakink000_gpt54thinking_short`, the Hunyuan mesh has three components:


rank 0: 135676 faces
rank 1: 10610 faces
rank 2: 3714 faces


Rank 0 is the dominant component, but it may still be a composite shape.

Therefore, the Hunyuan initial mesh should not be blindly treated as a clean object-only mesh.

## Design implication

The selector should not directly select the full Hunyuan HOI mesh as the final object candidate.

A better selector should use object-only candidates, or explicitly separate object geometry from hand / extra components before selection.  
