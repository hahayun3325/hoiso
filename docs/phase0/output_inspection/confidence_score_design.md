# Confidence Score Design for Object Source Selection

## Goal

Select the most reliable object source among multiple pipeline stages.

## Candidate sources

- inpaint-conditioned Hunyuan initial object
- final guided object
- post-processed final object
- future category/object prior

## Object confidence

C_obj =
  w_complete C_complete
+ w_silhouette C_silhouette
+ w_point C_point
+ w_text C_text
+ w_contact C_contact
- w_penetration P_penetration

## Completeness confidence

C_complete =  alpha * largest_face_ratio+ (1 - alpha) / components

## 2D silhouette confidence

C_silhouette = IoU(rendered_object_silhouette, completed_object_mask)

## 3D point confidence

C_point = exp(-Chamfer(rendered_object_surface, MoGe_visible_point_cloud))

## Text / semantic confidence

C_text = agreement(object_description, rendered_or_inpainted_object_shape)

## Contact confidence

C_contact = exp(-mean_distance(contact_fingers, object_surface))

## Penetration penalty

P_penetration = hand_object_intersection_volume

## Decision rule

if C_final < C_initial - delta:    fallback to initial object sourceelse:    keep final object

## Important principle

The selected object geometry should be preserved. Alignment should be improved by optimizing object SE(3), hand pose, and verified local contact, not by globally deforming object latent/SDF.  
