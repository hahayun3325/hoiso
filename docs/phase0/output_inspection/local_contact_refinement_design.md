# Local Contact Refinement Design

## Goal

Improve hand-object alignment without destroying object geometry.

## Key idea

Do not optimize object latent/SDF globally.

Instead:

- keep object mesh fixed,
- optimize object SE(3) pose,
- optimize hand global pose,
- optionally optimize only selected MANO finger pose parameters,
- apply contact attraction only to verified contacting fingers.

## What local means

Local means the contact loss is applied only to selected contact fingers and nearby object regions.

It does not mean deforming the entire object mesh.

## Suggested loss

L = λ_contact L_contact
  + λ_collision L_collision
  + λ_pose L_pose_reg
  + λ_obj L_object_pose_reg

## Variables to optimize

First version:

- object rotation
- object translation
- object scale
- hand global rotation
- hand global translation

Optional later version:

- selected finger joints only

## Variables to keep fixed

- object mesh topology
- object shape
- object latent / SDF
- MANO shape
- non-contact finger pose

## Why this helps

This preserves the good Hunyuan object shape while still allowing contact and alignment correction.  
