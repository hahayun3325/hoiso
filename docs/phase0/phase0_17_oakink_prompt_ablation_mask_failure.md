# Phase 0.17 — OakInk Prompt Ablation Mask Failure  
  
## What happened  
  
The manual LLM prompt run for `oakink000_gpt54thinking_template` loaded the manual prompt correctly, but preprocessing failed:  
  
```text  
No masks for oakink. Skipping.  
FileNotFoundError: No image files found in cropped_hoi_imgs_wo_bckg

## Root cause

The pipeline currently uses the same object description for two different roles:

1. object detection / segmentation prompt,
2. inpainting / reconstruction prompt.

The detailed structured prompt is useful for reconstruction, but it can be too long and too specific for the detector/segmenter.

## Fix for controlled prompt ablation

Reuse the successful baseline OakInk crop/mask outputs for all prompt-ablation runs.

This keeps segmentation fixed and changes only the object-description prompt used by inpainting/reconstruction.

## Interpretation

This is not a config failure.

It reveals a useful design lesson:

Detection prompts and reconstruction prompts should be separated.

