# alapuse02_v3b shared-frame dry-run v1 final decision

## Decision

FAIL_SHARED_FRAME_POST_HUNYUAN

## Observation

The v3b segmentation/mask repair succeeded, and the raw Hunyuan reference mesh
is a recognizable open laptop.

However, the shared-frame dry-run still fails. The scene legend is:

- green: guidance_out hand
- gray: aligned_mano reference hand
- blue: raw Hunyuan HOI mesh reference
- white: guidance_out object

The good-looking laptop in the scene is the blue raw Hunyuan reference, not
necessarily the final white guidance_out object consumed by Gate A/C/D.

## Metrics

The hand-to-guidance-object distance is too large:

- min ≈ 0.595
- mean ≈ 0.847
- within 10/20/50 cm = 0

## Interpretation

This is not the original segmentation failure anymore.

The current failure is downstream of Hunyuan:

raw Hunyuan laptop is good,
but the final shared-frame guidance object is not aligned with the hand.

Likely area to inspect:

- Hunyuan-to-MoGe h2m alignment
- MoGe target quality
- guidance_out object transform/export

## Next

Do not run Gate A/C/D on this output yet.

Run Gate A0 Hunyuan/frame sanity diagnostics to localize where the corrected
Hunyuan laptop becomes unusable.
