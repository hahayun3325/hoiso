# alapuse01 — Gate D contact scorer v0 semantic warning

## Decision

Contact-aware scorer v0 passes as a geometry/distance dry-run, but it is not accepted for sandbox optimization yet.

## Evidence

The scorer reports:

- decision = PASS_CONTACT_SCORER_V0_PATCH_USABLE
- num_patch_vertices = 20
- all 20 patch vertices are within 20 mm
- mean distance = about 0.00555
- attraction loss = 0.0
- penetration_warning = true

## Visual issue

The contact markers appear around a base / penetration region rather than the desired screen / outer top-lid contact shown in the input image.

## Interpretation

The scorer mechanics work, but the semantic contact target may be wrong.

The current target was built from the nearest hand patch to the active screen mesh. If the active screen mesh contains base-like geometry or the nearest screen component is not the desired top-lid surface, the scorer can pass numerically while selecting the wrong semantic target.

## Decision boundary

Allowed claim:

- contact scorer v0 can construct and score a reusable local mesh-patch contact target.
- the patch is geometrically close to the selected object surface.

Not allowed claim:

- the selected patch is confirmed to be the desired screen/top-lid contact.
- the result is ready for sandbox optimization.
- the contact-aware scorer solves semantic contact selection.

## Next step

Run Gate C v3.2 semantic contact-part audit.

The sandbox run remains paused until the target contact part is semantically verified.
