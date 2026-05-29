# Phase 0.15c — Fallback Stage Clarification

## What has been implemented

The current confidence-guided fallback is a post-hoc correction module.

It runs after the final guided object has already been produced.

Current steps:

1. compare object candidates,
2. compute object completeness / fragmentation score,
3. select the trusted object source,
4. reject fragmented final object,
5. roughly align selected object using bbox center and scale,
6. combine selected object with final hand for visual inspection.

## What has not yet been implemented

The current module does not modify FollowMyHold's internal Phase 4.2 or Phase 4.3.

It does not yet ask rectified flow to optimize only local object regions.

It does not yet perform contact-aware SE(3) refinement.

## Current conclusion

The fallback selector fixes object completeness.

The bbox alignment gives a visually reasonable pose, but it is still diagnostic.

## Next goal

Implement contact-aware SE(3) alignment:

- keep selected object geometry fixed,
- optimize object rotation / translation / scale,
- optimize hand global pose if needed,
- apply contact loss only to verified contact fingers,
- evaluate contact distance, penetration, and silhouette agreement.
