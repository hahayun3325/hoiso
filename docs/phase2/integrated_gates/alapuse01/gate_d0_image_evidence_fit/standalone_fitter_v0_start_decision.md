# alapuse01 — standalone fast articulated fitter v0 start decision

## Decision

Proceed from Gate A clean-parts v1 to standalone fast articulated fitter v0.

## Reason

Gate A v1 is semantically better than v0 and is now active. It is not perfect, but it is good enough to test the articulated fitting idea safely outside FollowMyHold.

## Current goal

Do not modify FollowMyHold yet.

First create a standalone fitter that can load:

- active screen/base/hinge parts
- object mask / image evidence
- current object and hand outputs

## V0 checkpoint

The first checkpoint is only input sanity:

- all expected files exist
- active parts load correctly
- diagnostic GLB is visually understandable
- screen/base/hinge are in the expected coordinate frame

## Next checkpoint

After v0 dry-run passes, implement the first real fitter:

- shared scale s
- keyboard_base root pose T_base
- screen hinge angle theta
- geometry + hinge scoring first
- image silhouette scoring second
