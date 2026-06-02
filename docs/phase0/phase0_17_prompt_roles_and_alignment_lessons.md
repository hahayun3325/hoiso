# Phase 0.17 — Prompt Roles and Alignment Lessons

## Prompt roles in the current pipeline

The current FollowMyHold-style pipeline uses the object description in multiple places.

## 1. Detection / segmentation prompt

The object description is used as a query for hand-object crop and segmentation.

A short object category works better here.

Example:

spray bottle

## 2. Inpainting / reconstruction prompt

The object description is also used by the inpainting stage to decide what object should remain after removing the hand.

A detailed geometry prompt is useful here.

Example:

A translucent spray bottle with a rounded tapered body, narrow neck, white trigger head, smooth plastic surfaces, and no boxy flat faces.

## CLIP length limitation

The inpainting model uses a CLIP-style text encoder.

The limit is **77 tokens**, not 77 words.

A token can be a full word, part of a word, punctuation, or a special token.

Therefore, a safer practical rule is:

35–55 wordsbelow roughly 350 charactersone concise sentenceone negative shape constraint

## Design lesson

Detection prompts and reconstruction prompts should be separated.

detection_prompt = short object categoryreconstruction_prompt = detailed geometry description

## Selector lesson

The selector chooses the object source with better completeness.

It is not a hard-coded Hunyuan fallback.

For OakInk split000, some prompts select the final object and some prompts select the initial object.

This shows the selector is confidence-based.

## Current post-hoc selector limitation

The current selector mainly decides which object geometry to trust.

It does not fully solve object-hand alignment.

The current post-hoc fallback can place the selected object near the hand, but it can still produce incorrect front/back or contact relationships.

A second issue is that the Hunyuan initial mesh may be a composite HOI mesh instead of a clean object-only mesh. If the selector directly uses the full Hunyuan HOI mesh as the object candidate, then the selected scene can contain extra non-object geometry plus the final hand.

## Refined design

Use the selector before final alignment, not as blind post-hoc scene replacement.


Phase 4.2 object-focused refinement→ object selector→ Phase 4.3 contact-aware alignment refinement→ scene validator


## Future HOISO-Flow direction

The selector should choose a reliable object candidate.

The following HOISO-Flow contact-guided refinement should solve the detailed hand-object alignment.

The final validator should check whether the scene is believable.  
