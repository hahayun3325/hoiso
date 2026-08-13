# `alapuse02v3n60`: shared Hunyuan/MoGe input and transform contract

## Purpose

This note records the Gate-C recovery that separated final geometry, relative-pose
evidence, image-frame placement, and residual optimization.  It prevents reuse of a
transform with the wrong source frame and prevents a color heuristic from becoming an
object-fit target.

## Roles

- **Gate A (`G`)** owns the accepted, part-aware laptop geometry and topology.
- **Clean Hunyuan HOI carrier (`U_hoi`)** is disposable coarse evidence for the
  upper-hand/laptop relative pose.  Its flawed laptop surface is never final output.
- **Fresh MoGe (`I`)** owns image-aligned 3D support, depth gauge, and FOV for the same
  accepted observation.
- **Frozen upper hand** remains the authoritative hand geometry in `I`.

## Shared-observation rule

Hunyuan and MoGe must be derived from the same accepted crop and foreground semantics;
they do not need to be rerun on every worksheet.  Hunyuan consumes the accepted RGBA
foreground.  MoGe consumes the deterministic white-background RGB derivative of that
same foreground.  Reuse is allowed only when input hashes, crop, masks, model/runtime,
and outputs remain current and reproducible.  Regenerate only a missing, stale,
contaminated, mismatched, or rejected branch.

For this case, the fresh Hunyuan carrier, fresh MoGe target, and fresh global
`T_Uhoi_to_I` are already accepted for support audit and must be preserved.

## Transform chain

The required composition is:

```text
T_G_to_I = T_Uhoi_to_I @ T_G_to_Uhoi
```

`T_Uhoi_to_I` globally places the disposable hand-laptop carrier into MoGe with one
proper uniform similarity.  `T_G_to_Uhoi` places only the trusted Gate-A laptop into
the carrier's laptop slot.  The composition is applied exactly once before residual
object optimization.  No reflection, anisotropic scale, per-part scale, or independent
hinge deformation is allowed in this bridge.

## Rejected ownership diagnostic

The first carrier support classifier inferred hand pixels from RGB chroma.  It produced
3,620 object, 2,038 upper-hand, 17,980 ambiguous, and 51,362 hidden vertices.  Ambiguity
was 76.06% of visible vertices and covered major lid/base/arm regions; red and green
labels were scattered over incorrect surfaces.  This partition is rejected for Gate-A
fitting, while the global `T_Uhoi_to_I` remains preserved.

The repair uses the exact accepted cleaned masks: object-only, upper-hand-only,
object/hand overlap, outside-union spill, and hidden.  The overlap is retained as a
contact/occlusion label, and fresh MoGe validity remains a separate property.

## Fit and execution gates

An exact-mask vertex view is diagnostic only.  Before fitting Gate A, create dense
deterministic face support or a proper face raster and require coherent object-owned
coverage of both lid and base, correct hinge/orientation, localized overlap, and limited
outside-union spill.  Fit Gate A only to object-owned carrier support; use upper-hand
contact and collision as validation gates, not as forces that pull the object.

After composing `T_G_to_I`, render the trusted Gate-A laptop with the frozen hand in
the exact current camera and accept a corrected zero-step state.  Only then run one
bounded `0/5/0` object-only stability test, followed by bounded joint refinement and
Gate D if the result remains acceptable.

## General lesson

A plausible global registration does not automatically supply trustworthy local
semantic correspondence.  Asset quality, transform ownership, observation provenance,
semantic support, and optimizer authorization are separate contracts and must close in
that order.
