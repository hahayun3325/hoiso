# Object branch, Flux, Hunyuan, and gate ordering

## Key lesson

Object reconstruction and shared-frame optimization should be separated.

For articulated objects like laptop_use, a clean object-only Hunyuan branch
can produce a useful part-aware Gate A input even when the final
guidance_out shared-frame object is bad.

## Flux / inpainting role

Flux inpainting is useful for completing occluded object appearance and
removing hands. However, it is not automatically trustworthy:
  - it may preserve or hallucinate background;
  - it may change object orientation;
  - it may produce an image that is visually good but not ideal for 3D
    reconstruction.

Therefore Flux output should be verified before it is passed downstream.

## Hunyuan role

Hunyuan should be treated as an object-shape generator when given a clean
object-only image. A clean Hunyuan mesh can be used for early Gate A
part decomposition before final hand-object optimization.

## Recommended gate order

1. Segmentation / mask sanity check.
2. Inpainting or object-only image sanity check.
3. Hunyuan object-shape sanity check.
4. Gate A part decomposition.
5. Shared-frame hand-object alignment check.
6. Gate B semantic contact proposal.
7. Gate C 3D contact verification.
8. Gate D contact/collision optimization.

## AGILE-style VLM verification

AGILE-style VLM/LLM verification should be added later as a model
coordination module.

For the current timeline, keep it deferred:
  first prove the gates,
  then add VLM verification to decide whether each foundation-model output
  is safe to pass into the next stage.
