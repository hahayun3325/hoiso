# Fallback Object + Local Contact Refinement Plan

## Goal

Use the good object shape from an earlier stage and improve alignment without damaging geometry.

## Step 1: Object source selection

Use object completeness score to choose between:

- Hunyuan initial object / object candidate
- final guided object
- post-processed object

## Step 2: Reject fragmented final object

Initial rule:

if components > 2 or fragmentation_score > 1.5:
    reject final object

## Step 3: Preserve selected object shape

Do not optimize object latent, SDF, topology, or mesh vertices.

## Step 4: Optimize alignment

Optimize only:

- object rotation
- object translation
- object scale
- hand global pose
- selected contact finger pose if needed

## Step 5: Local contact loss

Use contact constraints only for verified contacting fingers and nearby object surface points.

## Step 6: Evaluation

Check:

- contact distance
- penetration
- object silhouette IoU
- 3D object completeness
- visual hand-object alignment  
