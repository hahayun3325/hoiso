# Phase 0.17 — ARCTIC Selected Image Provenance

## Purpose

The ARCTIC phase 0.17 input images were manually selected and renamed to short case IDs:

- `abox01.jpg`
- `aket01.jpg`
- `ascis01.jpg`
- `alapuse01.jpg`
- `amicuse01.jpg`

For paper-like evaluation, each renamed image must be mapped back to its original ARCTIC source:

`subject / sequence / view_id / frame`

## Current provenance candidates

| case | object | source candidate | status |
|---|---|---|---|
| abox01 | box | `s01/box_grab_01/2/00081.jpg` or `s01/box_grab_01/2/00082.jpg` | verify by pixel diff |
| aket01 | ketchup | `s01/ketchup_grab_01/7/00147.jpg` | visually/hash verified |
| ascis01 | scissors | `s01/scissors_grab_01/5/00364.jpg` or `s01/scissors_grab_01/5/00365.jpg` | verify by pixel diff |
| alapuse01 | laptop | `s01/laptop_use_01/0/00114.jpg` | visually/hash verified |
| amicuse01 | microwave | `s01/microwave_use_01/0/00152.jpg` | visually/hash verified |

## Important note

The input-generation script previously recorded:

- `abox01 -> 00082.jpg`
- `ascis01 -> 00365.jpg`

The visual/hash search suggested adjacent frames for these two cases. Therefore, exact pixel comparison should be used as the final source of truth.

## Evaluation status

This provenance mapping is necessary but not sufficient for paper-style evaluation. We still need GT files:

- `meta`
- `object_vtemplates`
- `raw_seqs` or `splits`
- camera parameters
- hand/object pose annotations
