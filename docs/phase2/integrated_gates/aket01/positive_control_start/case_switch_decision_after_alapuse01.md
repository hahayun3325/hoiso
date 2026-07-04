# Case switch after alapuse01

## Decision

Use aket01 as the next active integrated-gates case.

## Why not continue alapuse01 immediately?

alapuse01 is now a characterized hard negative.

The v1b1 lid-targeted residual correction showed that correct lid/screen contact requires about 12.5–13 cm residual motion, which is too large for local contact-aware refinement. This means the current frame/initialization should not be used for full Gate D optimization.

## Why not amicuse01 next?

amicuse01 preflight failed:

- no active clean parts
- no part mesh PLY files
- no GLB visual scenes

It has selector-related Phase 1 outputs, but not enough Phase 2 assets for the integrated Gate A→D sandbox.

## Why aket01?

aket01 preflight passed asset availability:

- part meshes exist
- visual scenes exist
- selector-related runs exist

aket01 is the best positive/control case to prove the integrated pipeline mechanics before returning to harder articulated cases.

## Planned ladder

1. aket01: positive/control full pass.
2. abox01: contact/penetration repair showcase.
3. ascis01 vs amicuse01: articulated-case preflight bakeoff.
4. optional later: revisit alapuse01 with clearer frame or template/CAD initialization.
