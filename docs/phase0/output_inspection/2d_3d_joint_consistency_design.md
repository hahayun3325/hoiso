# 2D–3D Joint Consistency Design

## Motivation

The final guided object can become fragmented because image-space guidance may overfit partial visible cues.

The pipeline should combine 2D evidence with 3D object-completeness evidence.

## 2D cues

- object mask
- completed / inpainted object silhouette
- depth or disparity map
- normal map
- RGB crop

## 3D cues

- object completeness score
- number of connected components
- largest component face ratio
- Chamfer distance to trusted object candidate
- MoGe partial point cloud agreement
- contact-region distance
- penetration / intersection volume

## Safer optimization principle

Do not optimize global object latent/SDF freely.

Instead:

1. select trusted object geometry,
2. keep object mesh fixed,
3. optimize object SE(3) pose,
4. optimize hand pose,
5. apply local contact refinement only to verified contact fingers.

## Rejection rule

If final object completeness is worse than the earlier object source, reject the final object.
