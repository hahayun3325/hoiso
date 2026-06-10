# Phase 0.17 — ARCTIC aket01 Overlay Coordinate Issue

## Problem

The first direct 2D overlay showed no visible annotation.

## Cause

The selected `aket01` input is a cropped/resized 1000x1000 image, but the split annotations are in original image coordinates.

Evidence:

- input image size: 1000x1000
- right hand y range: about 1852–1993
- left hand y range: about 1594–1739
- object keypoint y range: about 1415–1831

Therefore, all direct 2D annotation points are below the 1000x1000 image canvas.

## Fix

Apply the same ARCTIC crop transform before drawing 2D points.

The likely mapping is:

`bbox = [center_x, center_y, scale]`

`crop_side = scale * 200`

`point_crop = (point_original - top_left) * 1000 / crop_side`

## Visualizer note

The official ARCTIC visualizer failed because `aitviewer` is missing. This is not blocking the 2D overlay gate.
