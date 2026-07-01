# alapuse01 — standalone fast articulated fitter plan

## Purpose

Test the integrated Gate A-D object model before modifying FollowMyHold.

## Inputs

- Gate A active cleaned parts:
  - screen.ply
  - keyboard_base.ply
  - hinge.ply

## Variables

- shared object scale s
- keyboard_base root pose T_base
- screen hinge angle theta

## Constraints

- no independent screen translation
- no independent part scale
- screen rotates around hinge
- hinge remains connected to base/screen

## First version

Use geometry-only scoring first:

- bbox scale consistency
- hinge connectivity
- screen/base separation
- no-collapse guard
- optional GT diagnostics only for evaluation

## Later version

Add image evidence:

- object silhouette
- part silhouette
- depth/disparity if available
- verified contact after object frame is reliable

## Runtime target

Under 10 minutes. Avoid large grid search.
