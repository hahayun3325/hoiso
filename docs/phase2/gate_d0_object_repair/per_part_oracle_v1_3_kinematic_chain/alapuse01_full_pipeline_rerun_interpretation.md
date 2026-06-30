# Should we rerun the full pipeline?

## Short answer

A full rerun can help only after Gate D-0 object repair is added.

## Current understanding

The previous flow/object optimization produced a poor laptop pose.  
Part-aware reconstruction and contact-aware optimization may help, but contact alone cannot fix object scale, root pose, and hinge angle.

## Correct rerun condition

A useful rerun should include:

1. part-aware object representation
2. shared-scale object repair
3. base root pose repair
4. screen hinge-angle repair
5. contact attraction after object repair
6. collision/interpenetration relief after contact

## Incorrect rerun condition

Do not rerun only the old pipeline and expect contact loss to fix the object frame.

## Current decision

Before rerunning the full pipeline, implement and test Gate D-0 v1.3 kinematic-chain oracle.
