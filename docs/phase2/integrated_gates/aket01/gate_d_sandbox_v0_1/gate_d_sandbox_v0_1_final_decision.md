# aket01 Gate D sandbox v0.1 final decision

## Decision

PASS_STABLE_NO_MOVE_BEST.

## Evidence

The tiny contact/collision probe selected:

- best alpha = 0.0
- best translation = [0, 0, 0]
- translation_norm = 0.0
- best stats exactly match baseline stats
- very_close_growth_vs_baseline = 0

Baseline / best contact statistics:

- min distance ≈ 0.0026 m
- p5 ≈ 0.0064 m
- p10 ≈ 0.0082 m
- within_003 = 2
- within_005 = 16
- within_01 = 123
- within_02 = 378
- within_05 = 590

## Interpretation

The verified body contact is already stable.

The contact term correctly chooses not to move a good pose. This is a successful positive-control result.

## Limitation

This is not yet a true collision pass. The current script uses a very-close-distance proxy, not a signed-distance collision metric.

## Next step

Run v0.2 signed-distance collision audit.
