# alapuse01 — selector-v41 aligned diagnostic decision v1

## Status

The selector-v41 aligned diagnostic now runs successfully.

The earlier failure was caused by loading `gt_right_hand_points.ply` as a forced mesh. The GT right hand is a point cloud with 778 vertices, so the robust loader is correct.

## Visual observation

The selector-v41 aligned scene is now valid because it loads:

```text
selector_v41_aligned_hand
selector_v41_aligned_object
gt_right_hand
gt_object
````

The predicted hand aligns with the GT hand, but the selector-v41 object is shifted, smaller, and does not overlap the GT object well.

## Numeric comparison

Hand alignment is good for all methods:

```text
default hand center error        = 0.00337
gpt55 hand center error          = 0.00337
selector_v41 hand center error   = 0.00337
```

Object-to-GT quality is best for default:

```text
default object NN mean           = 0.04070
gpt55_selector object NN mean    = 0.05500
selector_v41 object NN mean      = 0.08391
```

Selector-v41 has the worst object center error:

```text
default object center error      = 0.10716
gpt55 object center error        = 0.12307
selector_v41 object center error = 0.20677
```

Selector-v41 object is also too small:

```text
selector_v41 object diag = 0.34298
GT object diag           = 0.44878
```

However, selector-v41 has the best hand-object center-distance error:

```text
default hand-object error        = 0.06671
gpt55 hand-object error          = 0.09130
selector_v41 hand-object error   = 0.02211
```

## Decision

```text
GT object metric reference: default is currently strongest.
Selector-v41: useful for contact-pipeline development, but not valid for claiming GT object improvement.
Gate D optimizer-v1: do not claim final GT improvement yet.
Next step: run contact-only optimizer-v1 as exploratory, then evaluate contact/local distance separately from GT object CD.
```

