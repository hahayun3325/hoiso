# Phase 0.17 — OakInk split000 View-ID Mapping Decision

## Sample

- Dataset: OakInk
- Split index: 000
- Image: `south_east_color_90.png`
- Sequence: `A01023_0001_0002`
- Timestamp: `2021-10-12-17-13-00`

## Annotation format

The image-level annotation is stored as per-frame / per-view files:

- `anno/hand_v`
- `anno/hand_j`
- `anno/general_info`
- `anno/obj_transf`
- `anno/cam_intr`

Each frame has four numeric annotation views: `0, 1, 2, 3`.

## Selected mapping

Based on GT hand projection overlay, the correct annotation for:

`south_east_color_90.png`

is:

`view_id = 1`

## Evidence

The projected GT hand vertices and joints from `view_id=1` align closely with the visible hand in `south_east_color_90.png`.

The GT object overlay using `obj_transf.pkl` and `cam_intr.pkl` from `view_id=1` also aligns with the visible spray bottle.

## Usage

For OakInk split000 paper-style qualitative and quantitative evaluation, use files from:

`gt_assets/oakink_image_annotation/selected_south_east_frame90/`

including:

- `hand_v.pkl`
- `hand_j.pkl`
- `obj_transf.pkl`
- `cam_intr.pkl`
- `general_info.pkl`
- `image.png`
- `view_id.txt`
