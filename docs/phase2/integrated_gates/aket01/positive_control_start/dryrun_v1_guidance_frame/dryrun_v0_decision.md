# aket01 dry-run v0 decision

## Decision

DRYRUN_FRAME_MISMATCH.

## Evidence

The current integrated dry-run scene shows the green hand far away from the bottle/object parts.

The script loaded:

- hand: aligned_mano/aket01_hamer_aligned_mano.ply
- object: guidance_out/aket01_obj.ply

These likely live in different coordinate families.

## Interpretation

Do not run Gate C contact verification on this scene.

## Next step

Create dry-run v1 using same-frame guidance_out hand and guidance_out object first.
