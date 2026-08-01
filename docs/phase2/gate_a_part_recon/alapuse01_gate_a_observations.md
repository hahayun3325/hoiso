# Gate A — alapuse01 PartField observations

## Status

`alapuse01` is the first articulated-style Gate A test case.

The expected schema parts are:

```text
screen
keyboard_base
hinge
````

The PartField pipeline completed:

```text
selector_v41 object mesh
→ low30k decimation
→ PartField inference
→ 6-cluster over-segmentation
→ colored cluster inspection
→ manual vmap merge
→ named part export
→ quality and coverage reports
```

## Visual observation

The colored cluster scene shows meaningful laptop-like structure:

```text
screen-like vertical panel
keyboard/base-like horizontal panel
hinge/transition area
residual table/artifact/fragments
```

This is stronger than `aket01` because the object has natural articulated parts.

## Current merge interpretation

The first manual merge used:

```text
screen: [3, 4]
keyboard_base: [2]
hinge: [1]
residual_uncertain: [0]
```

However, this left cluster 5 unused, so the geometry coverage was incomplete.

The geometry-preserving merge should include all clusters:

```text
screen: [3, 4]
keyboard_base: [2]
hinge: [1]
residual_uncertain: [0, 5]
```

## Judgment

`alapuse01` is a promising Gate A articulated test. The visual part separation is meaningful, but final Gate A pass should be decided after the v2 geometry-preserving quality and face coverage reports.
