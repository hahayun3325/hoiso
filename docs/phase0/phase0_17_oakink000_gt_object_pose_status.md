# Phase 0.17 — OakInk split000 GT Object Pose Status

## Current status

The OakInk split000 image, object mesh, and candidate MANO hand parameters have been located.

The strongest candidate hand/object instance is:

- object id: `A01023`
- instance folder: `d846cc7ddf`
- candidate hand: `s01102/hand_param.pkl`

The `source.txt` file points to:

`pass1/A01023_0001_0002/2021-10-12-17-13-00/dom.pkl`

## Missing piece

The actual `dom.pkl` file has not been found locally.

This file likely contains the image-level annotation needed for official evaluation:

- camera intrinsics/extrinsics
- object pose for the frame
- MANO hand pose in camera/world coordinates
- frame/view-specific transforms

## Interpretation

The current qualitative panel is not a GT panel yet. It shows pipeline predictions, not official OakInk GT object pose.

## Next step

Find or extract the OakInk-Image annotation archive, likely `anno_v2.1.zip`, and inspect the exact `dom.pkl` file for split000.
