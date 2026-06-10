# Phase 0.17 — ARCTIC First-Case Evaluation Decision

## Current status

The first ARCTIC case, `aket01`, is ready for a paper-like metric dry run.

Evidence:

- official 2D crop transform works
- manual and official transforms differ by less than 2 px
- processed GT file contains:
  - `cam_coord/verts.object`
  - `cam_coord/verts.left`
  - `cam_coord/verts.right`
- Kaolin import works again after downgrading NumPy back to 1.24.0

## Important caution

The first metric should be treated as a dry run, not as a final reportable paper-style number.

The remaining key issue is coordinate alignment between FollowMyHold prediction meshes and ARCTIC GT camera-space meshes.

## Next steps

1. Run `aket01` first metric dry run.
2. Generate 2D overlays for all five selected cases.
3. Process GT vertices for the other four sequences.
4. Only after overlays pass for all cases, compute an all-case ARCTIC metric table.
