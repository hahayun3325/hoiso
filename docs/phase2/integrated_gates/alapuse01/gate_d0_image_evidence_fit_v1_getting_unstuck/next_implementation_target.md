# Next implementation target

## Decision

Implement Gate D-0 v1 image-evidence articulated fitting.

## Why not Gate D sandbox?

The current contact target is geometrically close but semantically wrong.

Sandbox optimization would reinforce the wrong contact between the hand and a base-like fragment.

## Why not more Gate C?

Gate C v3.3 already tested the manually selected true top-lid component.

The true top-lid is far from the hand patch, so the current object state does not support the desired contact.

## Immediate implementation order

1. Build a part-label audit/relabel script using image/mask evidence.
2. Save a corrected semantic part map:
   - lid_outer_surface
   - keyboard_base
   - hinge
   - discard board/residual fragments
3. Build a small articulated fitting script:
   - fixed or initialized small lid angle
   - optimize {s, T_base, theta}
   - use image-derived contact prior
   - penalize hand-through-base and inter-part penetration
4. After fitting, rerun Gate C contact verification.
5. Only then run Gate D sandbox/contact-aware optimization.

## Circuit breaker

No more Gate C target variants unless the object state has changed.
