# alapuse01 — Gate D-0 per-part oracle v1 judgement

## Decision

Gate D-0 per-part oracle v1: PARTIAL PASS.

## Positive evidence

The shared-scale per-part oracle avoids the severe collapse from the previous global oracle repair.

Key metrics:

- whole collapse_flag = false
- whole pred_to_gt_mean = 0.0165
- whole gt_to_pred_mean = 0.0227
- bbox_volume_ratio = 1.55
- F50 = 0.901

This confirms that shared-scale per-part repair is a promising model class.

## Limitation

The visual scene is not physically clean. The screen, keyboard base, and hinge are twisted / overlapping / not connected.

The metric file also shows that each part used the whole GT object as a proxy target:

- screen -> whole_gt_proxy_no_gt_part_label
- keyboard_base -> whole_gt_proxy_no_gt_part_label
- hinge -> whole_gt_proxy_no_gt_part_label

Therefore, this result cannot be accepted as a clean object repair.

## Interpretation

V1 proves that per-part motion helps, but it is too loose.

The next model must enforce laptop articulation:

- one shared global scale
- keyboard_base root pose
- screen rotation around hinge
- connected hinge constraint
- no independent screen translation
- no independent per-part scale

## Next step

Implement Gate D-0 per-part oracle v1.1 with connected hinge constraint.

Contact/collision optimization remains paused.
