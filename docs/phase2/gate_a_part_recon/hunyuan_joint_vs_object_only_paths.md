# Hunyuan joint HOI path vs object-only Gate A path

## Normal FollowMyHold path

FollowMyHold calls Hunyuan on the background-stripped hand-object crop:

  cropped_hoi_wo_bckg -> Hunyuan HOI mesh

This is intentional. The output is a coarse joint hand-object mesh that helps
the later guidance stage reason about hand-object arrangement.

This mesh is not guaranteed to be separable into hand and object by connected
components. When hand and object touch, Hunyuan may decode them as one
topologically connected surface.

## Inpainting path

The inpainted object image removes hands and completes the object appearance
in 2D. It is used as an appearance/reference signal for the guidance stage.

Important warning:
  FLUX may silently change output resolution. Therefore, do not assume
  ours_inpaint/*.png is pixel-aligned with cropped_obj_mask.png unless image
  dimensions are explicitly checked.

## Gate A-early object-only path

Gate A needs clean object geometry and object parts. It does not need the final
hand-object shared frame.

For Gate A, create an object-only Hunyuan input by compositing:

  cropped_hoi_wo_bckg + cropped_obj_mask -> object_only_white.png

Requirements:
  - same image size before compositing
  - pure white background
  - no hands, arms, table, cables, truss, or background objects
  - object pose and visible structure preserved

Then run one-shot Hunyuan on this object-only image.

## Decision rule

Use normal Hunyuan HOI path for:
  - shared-frame HOI initialization
  - Gate C/D contact-aware experiments

Use object-only Hunyuan path for:
  - Gate A part-aware reconstruction
  - screen/base/hinge part split
  - object integrity checks before optimization
