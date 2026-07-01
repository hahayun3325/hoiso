# alapuse01 — Gate A clean-parts v1 final decision

## Decision

Use Gate A clean-parts v1 component merge as the active part proposal.

## Reason

V0 keeps only the largest screen component and discards too much screen/lid area.

V1 keeps the two large screen components and drops the thin line component. This makes the screen/lid semantically more complete.

## Evidence

V0 screen:
- area = 0.3551
- vertices = 1968
- faces = 3944
- components = 1

V1 screen:
- area = 0.5412
- vertices = 4673
- faces = 9078
- components = 2

## Limitation

V1 is not a perfect clean part. The screen still has two disconnected components.

However, it is better than v0 for the next standalone articulated fitting stage because it preserves more of the lid/screen surface.

## Active cleaned parts

Use:

- active_clean_parts/screen.ply
- active_clean_parts/keyboard_base.ply
- active_clean_parts/hinge.ply

## Next step

Build standalone fast articulated fitter with:

- shared scale s
- keyboard_base root pose T_base
- screen hinge angle theta
- hinge/connectivity scoring
- later: silhouette/depth/image evidence
