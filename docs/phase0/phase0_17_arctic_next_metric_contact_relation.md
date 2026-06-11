# Phase 0.17 — Next Metric: Contact and Relative Pose

The current selected-case ARCTIC metrics show that the selector improves mean object CD after hand-based alignment.

However, the current evaluation does not directly prove better hand-object contact or alignment.

Next, we should add contact/relative-pose metrics:

- hand-to-object minimum distance
- hand-to-object 5th percentile distance
- hand-to-object mean distance
- object center relative to hand center
- object scale after alignment

These metrics will help separate:

1. object geometry quality
2. object pose relative to the hand
3. contact plausibility
