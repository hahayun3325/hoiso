# alapuse01 — Gate D-0 per-part oracle v1.1 final judgement

## Decision

Gate D-0 per-part oracle v1.1 connected hinge: PARTIAL PASS.

## Positive evidence

V1.1 fixes the major collapse / scale issue:

- collapse_flag = false
- bbox_volume_ratio = 0.9875
- bbox axis ratios are close to GT
- hinge_gap_p5 = 0.00527

This means the shared-scale connected-hinge model is more physically reasonable than the old global similarity repair.

## Remaining issue

The visual scene is still not a clean laptop repair.

The screen and base are still misaligned with GT, even though the scale and location are much better.

The best hinge angle is only 5 degrees, which suggests the estimated hinge axis / hinge center / base root pose is weak.

## Interpretation

V1.1 confirms that connected articulation is the right direction, but the hinge model is not accurate enough yet.

## Decision boundary

Allowed claim:

- v1.1 prevents collapse and improves scale consistency.
- connected hinge is a better model class than global object similarity.

Not allowed claim:

- v1.1 solves object repair.
- v1.1 is ready for Gate C v3 contact verification.
- final contact geometry is reliable.

## Next step

Proceed to Gate D-0 per-part oracle v1.2 hinge-axis refinement.

Gate C v3 contact verification remains paused.
