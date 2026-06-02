# Phase 0.17 — Prompt Roles and Alignment Lessons

## Prompt roles in the current pipeline

The current FollowMyHold-style pipeline uses the object description in multiple places.

### 1. Detection / segmentation prompt

The object description is used as a query for hand-object crop and segmentation.

A short object category works better here.

Example:

spray bottle

### 2. Inpainting / reconstruction prompt

The object description is also used by the inpainting stage to decide what object should remain after removing the hand.

A detailed geometry prompt is useful here.

Example:


A translucent spray bottle with a rounded tapered body, narrow neck, white trigger head, smooth plastic surfaces, and no boxy flat faces.


## Design lesson

Detection prompts and reconstruction prompts should be separated.


detection_prompt = short object categoryreconstruction_prompt = detailed geometry description


## Selector lesson

The selector chooses the object source with better completeness.

It is not a hard-coded Hunyuan fallback.

For OakInk split000:

- some prompts select final object,
- some prompts select initial object.

This shows the selector is confidence-based.

## Alignment limitation

The current selector mainly decides which object geometry to trust.

It does not fully solve object-hand alignment.

The fallback alignment currently uses rough bbox-based alignment, which can place the selected object near the hand but still produce incorrect front/back or contact relationships.

## Future fix

Add a local contact-aware alignment stage after object selection:

1. preserve selected object geometry,
2. optimize object SE(3),
3. optimize hand global pose,
4. use MoGe depth / rendered mask / verified contact points,
5. reject alignments with wrong occlusion or poor contact.  
