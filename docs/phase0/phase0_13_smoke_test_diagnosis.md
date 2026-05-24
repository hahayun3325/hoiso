# Phase 0.13 — Smoke Test Diagnosis

## Current status

The environment dependency issues are mostly resolved. The current blocker is preprocessing.

## Observed failures

- Gemini query works.
- WiLoR can detect hand boxes in some HO3D images.
- hand_object_detector often returns `object_bbox=None`.
- When object detection fails, preprocessing cannot create masks/crops.
- The pipeline should not proceed to full reconstruction until preprocessing outputs exist.

## Important artifacts needed before full inference

The following files must exist before running later stages:

- `cropped_hoi_imgs/*.png`
- `cropped_hand_masks/*.png`
- `masked_obj_imgs/*.png`
- `cropped_hoi_imgs_wo_bckg/*.png`

## Dataset note

FollowMyHold evaluates on OakInk, ARCTIC, and DexYCB, not HO3D. HO3D may be useful for stress testing, but it is not the best first reproduction target.
