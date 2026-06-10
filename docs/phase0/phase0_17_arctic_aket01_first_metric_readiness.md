# Phase 0.17 — aket01 First Paper-Style Metric Readiness

## Best 2D annotation transform

For the selected cropped `aket01` input, use the ARCTIC crop transform:

- `center = bbox[:2]`
- `scale = bbox[2]`
- `res = [1000, 1000]`
- official helper: `common.data_utils.transform`

The diagnostic grid shows the best transform is `side = scale * 200`.

## Important distinction

ARCTIC `crop_images.py` can create loose crops using `bbox[:, 2] *= 1.5`, but the selected `cropped_images_structured` input aligns best with `scale * 200`.

## Current status

Ready for:

- official-transform 2D overlay
- one-case metric dry run preparation

Not ready for:

- reportable all-case ARCTIC paper-style metric table

## Next gate

Inspect `outputs/processed_verts/seqs/s01/ketchup_grab_01.npy` for dense GT hand/object vertices.

Then compute aket01 only:

- default vs GT
- GPT-5.5+selector vs GT
