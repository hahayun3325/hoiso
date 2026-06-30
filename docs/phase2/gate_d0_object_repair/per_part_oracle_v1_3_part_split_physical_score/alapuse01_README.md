# alapuse01 — Gate D-0 per-part oracle v1.3

## Goal

Improve v1.2 by adding stronger part-aware and physical scoring.

## Why v1.3 is needed

V1.2 improves numeric alignment and avoids collapse, but the visual result is physically wrong:
screen, base, and hinge penetrate / cross / misalign.

## V1.3 target

Add:

1. better pseudo-GT screen/base split
2. inter-part penetration / crossing penalty
3. hinge-connectivity penalty
4. comparison against v1.1 and v1.2
5. visual diagnostics for top candidates

## Success condition

V1.3 passes only if:

- collapse_flag remains false
- bbox volume stays reasonable
- screen/base visually align better with GT
- screen and base do not penetrate badly
- hinge remains connected
- object frame becomes reliable enough for Gate C v3

## If v1.3 passes

Run Gate C v3 contact verification in the repaired frame.

## If v1.3 fails

Move toward image/silhouette-based scoring and inspect Gate A part quality.
