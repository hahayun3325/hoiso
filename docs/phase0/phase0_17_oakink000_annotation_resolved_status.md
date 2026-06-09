# Phase 0.17 — OakInk split000 Annotation Resolved Status

## New finding

The expected old `dom.pkl` layout is not used by the local `anno_v2.1.zip`.

Instead, the image-level annotation is stored as per-frame / per-view files under:

- `anno/hand_v`
- `anno/hand_j`
- `anno/general_info`
- `anno/obj_transf`
- `anno/cam_intr`

## OakInk split000 frame 90

For `A01023_0001_0002 / 2021-10-12-17-13-00 / frame 90`, the annotation archive contains 20 files:

- 4 hand vertex files
- 4 hand joint files
- 4 general info files
- 4 object transform files
- 4 camera intrinsic files

## Remaining issue

The remaining issue is not annotation availability. It is view-id mapping:

`south_east_color_90.png` must be mapped to one of the numeric view ids `0,1,2,3`.

## Next step

Use GT hand projection overlays to identify the correct numeric view id, then export the selected GT hand/object/camera annotation files for official-style qualitative and quantitative evaluation.
