# alapuse01 — Gate D-0 diagnostic v2 final decision

## Decision

Gate D-0 diagnostic v2 metrics: PASS.

The old oracle similarity repair is rejected as collapsed / unreliable.

## Evidence

The old oracle repair has a good one-way pred-to-GT distance:

- pred_to_gt_mean = 0.01038

But the new v2 metrics reveal the failure:

- gt_to_pred_mean = 0.05385
- symmetric_mean = 0.03211
- asymmetry_ratio = 5.19
- bbox_volume_ratio = 0.203
- collapse_flag = true
- diagnostic_decision = REJECT_AS_COLLAPSED_OR_UNRELIABLE

## Interpretation

A low pred-to-GT nearest-neighbor distance is not enough.

The old oracle repair shrinks / twists the laptop so many predicted points are close to GT, but the repaired object does not cover the full GT object and does not preserve realistic laptop scale.

## Consequence

Do not use the old oracle-repaired object as a final object.

Do not resume contact/collision optimization yet.

## Next step

Proceed to per-part oracle upper bound v1.

Goal:

Can keyboard_base and screen/top_lid be aligned cleanly if they are allowed to move as separate articulated parts, instead of using one global similarity transform for the whole laptop?
