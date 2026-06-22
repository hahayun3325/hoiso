# New metrics: from object quality to HOI alignment

## Why CD / F-score are not enough

Object CD and F-score measure whether the reconstructed object shape is close to GT.  
However, HOI reconstruction also needs the object to be correctly placed **relative to the hand**.

A good-looking object can still fail if it is:

- floating far from the hand;
- penetrating the hand;
- placed on the wrong side of the hand;
- fragmented into disconnected pieces.

## Metric groups

### 1. GT reconstruction quality

Measures object shape quality after hand-based alignment.

- `object_cd_mm`: lower is better
- `object_f5`, `object_f10`: higher is better
- `hand_cd_mm`: sanity check for hand alignment

### 2. Physical contact quality

Measures hand-object physical plausibility.

- `contact_p5_mm`: 5th percentile hand-to-object distance
- `contact_mean_mm`: average hand-to-object distance
- `object_inside_hand_ratio`
- `hand_inside_object_ratio`
- max penetration depth in both directions

### 3. Object pose relative to the hand

This directly tests whether the object is correctly aligned in the HOI scene.

After aligning predicted hand to GT hand:

\[
e_{rel} =
\left\|
(c^{pred}_{obj} - c^{pred}_{hand})
-
(c^{gt}_{obj} - c^{gt}_{hand})
\right\|_2
\]

Reported as:

- `relative_object_center_error_mm`
- delta vs baseline
- delta vs selector + GPT-5.5

## Interpretation

This metric tells us whether selector-v4.1 gives the optimizer a better object pose, not only a better object shape.
