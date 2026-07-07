# Getting a clean object-only mesh for Gate A

## Two separate problems, don't conflate them

1. **Prompt specialization** (see per_model_prompt_specialization_note.md):
   segmentation models need short direct phrases; reconstruction/inpainting
   models handle long descriptive prompts fine.

2. **Image dimension/alignment mismatch** (this note): unrelated to prompts.
   FLUX Kontext inpainting silently overrides requested height/width to fit
   its own resolution requirements (observed: forced to 1024x1024 even when
   inpaint.py explicitly requested the original crop's dimensions). inpaint.py
   saves the returned image as-is, with no resize back to the original size.
   This means `ours_inpaint/*.png` may NOT share dimensions with
   `cropped_hand_masks/*_obj_mask.png`, even though both nominally describe
   the same crop region. Naively resizing the mask to match (or vice versa)
   silently distorts spatial alignment, causing a mask-based composite to
   grab the wrong image region entirely (observed: captured the white
   board/table instead of the laptop).

## Recommended recipe for a clean, white-background, object-only image

Do NOT composite using `ours_inpaint` + the object mask.

Instead, composite using two images from the SAME pre-FLUX preprocessing
stage, which are guaranteed to share dimensions:

- `cropped_hoi_imgs_wo_bckg/*.png` (scene background already stripped,
  hand still present)
- `cropped_hand_masks/*_obj_mask.png` (object-only mask, same stage)

```python
assert img.size == mask.size  # ALWAYS verify before compositing
out = white_canvas
out[mask] = img[mask]
```

This avoids FLUX entirely for this step — no hallucination risk, no
resolution mismatch risk.

## Early-warning check for next time

Before trusting any mask+image composite, print both images' `.size` and
assert they match. Do not resize one to fit the other without first
confirming they were meant to be aligned in the first place.
