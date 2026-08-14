# alapuse02v3n60: object/hand carrier-to-MoGe alignment and Gate-D contract

## Purpose

This note records the coordinate ownership and staged optimization route used
after auto-v2.  It distinguishes the standard FollowMyHold path from the
trusted Gate-A replacement path used for this case.

## Coordinate frames

- **G**: trusted Gate-A laptop geometry and part/hinge state.
- **H**: selected HaMeR/MANO hand geometry and articulation.
- **Uhoi**: disposable clean Hunyuan hand-object pose carrier.
- **I**: current image/camera-aligned MoGe frame.

For column points, transforms are source-to-target and compose from right to
left.  The shared carrier transform is `T_Uhoi_to_I`.  The hand endpoint is

`T_H_to_I = T_Uhoi_to_I @ T_H_to_Uhoi`.

Never invert this order, apply `T_Uhoi_to_I` twice, or transplant an H2M
matrix from a different carrier/MoGe pair.

## Paired input contract

Hunyuan and MoGe must observe deterministic derivatives of the same accepted
crop and foreground semantics.  Hunyuan consumes the accepted RGBA view;
MoGe consumes the white-composited RGB derivative.  Each input, model/runtime,
camera, point map, mask, transform, and output is hash-bound.  Reuse is allowed
when provenance remains exact; models are not rerun merely because a later
stage starts.

## Object route

Standard FollowMyHold uses the native Hunyuan object already in Uhoi and moves
it with `T_Uhoi_to_I`.

For this case, the fused carrier object was visibly coarse and its semantic
surface ownership was unreliable.  Gate-A was therefore fitted directly to
the fresh, exact-mask, object-only MoGe support:

`G --T_G_to_I--> I`.

The accepted CPU initializer is seed 2026.  It is a positive proper uniform
Sim(3), evaluated with the exact camera, visible object mask, MoGe depth, and
hand exclusion.  It is not assumed identical to the fused Uhoi object.

If a carrier-frame representation is needed without changing the accepted
endpoint, factor it algebraically:

`T_G_to_Uhoi = inverse(T_Uhoi_to_I) @ T_G_to_I`.

This factorization is diagnostic, not an independently learned object-carrier
fit.  A future G-to-Uhoi ablation must estimate and review its own transform
against object-owned support from the same clean carrier.

## Hand route

The selected upper hand comes from a spatially owned HaMeR detection.  Its
global historical MoGe pose was rejected, while MANO topology/articulation
remains the shape prior.  The official conceptual route is retained:

`H --T_H_to_Uhoi--> Uhoi --T_Uhoi_to_I--> I`.

Because the clean carrier hand is fused and only partly visible, hand fitting
uses several complementary owners:

1. ordered 21 HaMeR/MANO joints own 2D rotation/translation consistency;
2. the exact signed camera owns projection;
3. fresh MoGe upper-hand evidence owns metric depth;
4. the distal carrier support supplies a coarse lid-side anchor, not proven
   contact;
5. exact object/hand/overlap masks own visibility and excluded pixels;
6. immutable Gate-A owns collision and allowed contact geometry.

Free-scale ICP against 120 partial distal points was rejected because it
shrunk the full MANO mesh.  Fixed-scale PnP fixed 2D orientation but exposed
the monocular scale-depth gauge.  Camera-ray depth repair moved the hand into
the laptop depth band.  Bounded SE(3) and constraint-first CPU searches then
showed that no tested rigid candidate simultaneously passed joints, spill,
depth, support, and collision gates.  No rejected candidate is a CPU zero.

## Optimization route

The official project entrypoint is:

`PYTHONPATH=src python3 -m foho.main --config configs/pipeline.env`.

The official patched guidance implementation performs:

1. hand-only global transform refinement using HaMeR 2D keypoints and MoGe
   normal/disparity/silhouette evidence;
2. object transform/generative refinement;
3. joint hand-object refinement with image losses, proximity, and optional
   intersection loss.

Custom initializers must first be installed through a reviewed opt-in source
owner.  A capture-only live zero must prove the official renderer/loss sees
the exact CPU hand and object once, before backward or optimizer step.  A
short hand-only run comes next with Gate-A frozen.  Object-only and joint
updates remain separately authorized stages.

## Gate D

Gate D is the final contact/collision acceptance contract.  Its evidence may
be produced by a bounded contact-aware joint refinement, but the optimizer
and the gate must have separate receipts.  Gate D requires localized intended
lid/rim contact, no keyboard/base contact, no material penetration or wrong
z-order, no regression in keypoints/silhouette/depth/normal, unchanged asset
ownership/topology, and reproducible transform composition.  It is not a
rescue mechanism for a wrong frame, identity, scale, or coarse pose.

## Current status

- Fresh Hunyuan carrier, fresh paired MoGe target, signed camera, and
  `T_Uhoi_to_I` are accepted in their scoped roles.
- Gate-A seed 2026 is the preserved object initializer in I.
- No hand CPU zero is accepted.
- The `14_40` GPU diagnostic was unadjudicated because OpenCV EXR support was
  not enabled before import; its negative route is superseded.
- One replacement standalone hand `R,t` feasibility attempt is authorized
  only after an EXR decode preflight.  Official live flow, object flow, joint
  flow, and Gate D remain closed.

## Primary references

- Official repository and full entrypoint: https://github.com/aidilayce/FollowMyHold
- Official patched guidance implementation: https://github.com/aidilayce/FollowMyHold/blob/main/third_party_patches/hy3dgen/shapegen/pipelines.py
- Paper: https://openreview.net/forum?id=ZhuDHYZ5tv

