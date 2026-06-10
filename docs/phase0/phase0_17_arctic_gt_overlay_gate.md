# Phase 0.17 — ARCTIC GT Overlay Gate

## Current status

The ARCTIC GT/evaluation data has now been downloaded:

- `raw_seqs`
- `splits`
- `splits_json`
- `meta`
- `object_vtemplates`
- MANO/SMPL-X models

`processed_seqs` is still missing, but it is not yet confirmed to be required.

## Next gate

Before reporting paper-like metrics, validate one GT overlay:

`aket01 = s01 / ketchup_grab_01 / view 7 / frame 147`

The overlay must show:

- GT hand aligned with visible hand
- GT object aligned with visible ketchup bottle
- camera projection convention is correct

## Decision rule

If the `aket01` GT overlay matches the RGB image, then proceed to one-case paper-like metrics.

If it does not match, inspect official ARCTIC loader conventions before computing any metric.
