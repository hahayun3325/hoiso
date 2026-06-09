# Phase 0.17 — OakInk Annotation Format Update

## Previous assumption

We expected the OakInk image-level annotation for split000 to be stored as:

`pass1/A01023_0001_0002/2021-10-12-17-13-00/dom.pkl`

## New finding

After downloading `anno_v2.1.zip`, the archive does not expose that `dom.pkl` path.

Instead, it contains per-frame / per-view annotation files such as:

`anno/hand_v/A01023_0001_0002__2021-10-12-17-13-00__0__89__3.pkl`

Therefore, the official OakInk image annotation format available locally is not the old `dom.pkl` layout.

## Implication

The extraction failure was caused by a wrong internal path assumption, not a failed download.

## Next step

Inspect all split000 frame-90 annotation files inside `anno_v2.1.zip`, identify the view-id mapping for `south_east_color_90.png`, and locate object pose / camera parameters from the per-frame annotation files or official OakInk loader.

## Evaluation status

The missing annotation did not affect reconstruction quality. It only blocked official GT-based evaluation and GT overlay.
