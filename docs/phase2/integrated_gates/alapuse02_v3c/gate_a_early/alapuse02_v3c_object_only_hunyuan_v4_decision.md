# alapuse02_v3c object-only Hunyuan v4 decision

Decision:
  PASS_CLEAN_OBJECT_MESH

Evidence:
  - Corrected white-background object-only input was created from:
      cropped_hoi_wo_bckg + cropped_obj_mask
    not from the FLUX inpainted image.
  - This avoids the prior 1024x1024 vs 512x512 FLUX/mask resolution mismatch.
  - Hunyuan one-shot decode produced:
      75,002 vertices
      150,000 faces
      1 connected component
  - Visual inspection shows a recognizable open laptop with screen, base,
    and hinge structure.
  - No visible hands, arms, truss bars, cables, or table geometry remain.

Interpretation:
  This is the first clean object-only mesh for alapuse02_v3c.
  It is a valid Gate A input candidate.

Caveat:
  This is not the normal FollowMyHold HOI reconstruction path.
  It is a new Gate A-early object-only branch.
