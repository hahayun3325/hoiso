# Smoke 015 — Structured Prompt Ablation Status

## Main result

The structured rectangular SPAM prompt clearly improves the inpainted object.

Compared with the baseline smoke_013 result, the smoke_015 inpainted image better preserves:

- the boxy SPAM tin shape
- the flat front face
- the rounded rectangular corners
- the metal top
- the non-cylindrical object identity

## Interpretation

This supports the hypothesis that vague object descriptions can cause semantic drift in FollowMyHold-style pipelines.

The baseline prompt was:

A can of Spam.

This was semantically correct but geometrically vague.

The improved prompt was:

`A rectangular SPAM canned meat tin with flat front and back faces, rounded rectangular corners, and a metal top. The object is boxy and not a cylindrical soda can or soup can.`

## Current blocker

The full smoke_015 run does not yet produce final guidance meshes because it hits CUDA OOM inside Hunyuan guidance-time SDF decoding:

`latent2sdfvae.geo_decodercross_attn_decodertorch.OutOfMemoryError: Allocation on device`

This is different from the earlier final FlexiCubes OOM.

## Corrected conclusion

Smoke_015 is a successful prompt/inpainting ablation, but not yet a completed final-guidance reconstruction.

## Next step

Inspect the smoke_015 Hunyuan initial mesh, check mask-inpaint consistency, and rerun guidance-only with lower guidance-time memory settings.  
