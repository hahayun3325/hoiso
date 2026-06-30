# alapuse01 — Gate D-0 per-part oracle v1.2 final judgement

## Decision

Gate D-0 per-part oracle v1.2: PARTIAL PASS / VISUAL FAIL.

## Positive evidence

V1.2 improves some quantitative metrics compared with v1.1:

- collapse_flag = false
- symmetric_mean improves from 0.0382 to 0.0320
- F50 improves from 0.632 to 0.753
- bbox_volume_ratio = 1.258

This means the hinge-axis refinement improves numeric alignment and avoids collapse.

## Visual failure

The visual scene is still not a physically valid laptop.

The screen, keyboard base, and hinge penetrate / cross / misalign with each other.

Therefore v1.2 is not accepted as a clean repaired object frame.

## Interpretation

The next blocker is not only hinge-axis search.

The next blocker is part-aware physical scoring:

- better pseudo-GT screen/base split
- inter-part penetration penalty
- hinge connectivity penalty
- later, image/silhouette-based scoring

## Decision boundary

Allowed:

- v1.2 improves numeric alignment over v1.1
- v1.2 avoids collapse
- v1.2 shows that hinge-axis search is useful

Not allowed:

- v1.2 solves object repair
- v1.2 is ready for Gate C v3
- final screen/top-lid contact can be verified in this repaired frame

## Next step

Proceed to Gate D-0 v1.3:

pseudo-GT part split + physical inter-part scoring.

Gate C v3 remains paused.
