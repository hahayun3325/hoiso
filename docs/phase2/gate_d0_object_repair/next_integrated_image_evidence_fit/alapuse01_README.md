# alapuse01 — next direction: integrated image-evidence articulated fitting

## Decision

Stop post-hoc GT-Chamfer grid-search oracle.

Move toward a fast image-evidence fitting module, then integrate it into FollowMyHold.

## Motivation

The v1.1-v1.3 oracle line showed:

- one-way NN metric can be gamed
- free part motion gives inconsistent parts
- kinematic grid search is too slow
- fragmented parts remain a bottleneck

## Target model

Use:

- shared object scale s
- keyboard_base root pose T_base
- screen hinge angle theta
- optional hinge-axis prior or template
- no independent per-part scale
- no independent screen translation

## Target losses

Use image evidence:

- whole-object silhouette loss
- per-part silhouette loss if masks exist
- depth/disparity loss
- hinge connectivity loss
- inter-part penetration loss
- verified contact loss only after object pose is reliable

## Runtime target

No 6000-candidate grid.

Use:

- one coarse scale estimate
- one base-pose initialization
- one hinge-axis estimate
- 50-100 gradient steps

Target runtime: under 10 minutes.
