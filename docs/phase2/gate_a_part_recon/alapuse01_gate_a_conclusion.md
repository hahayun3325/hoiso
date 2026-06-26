# Gate A — alapuse01 conclusion

## Status

`alapuse01` is the first articulated-style Gate A case.

Expected semantic parts:

```text
screen
keyboard_base
hinge
residual_uncertain
````

## Completed pipeline

```text
selector_v41 object mesh
→ low30k decimation
→ PartField inference
→ 6-cluster over-segmentation
→ colored cluster inspection
→ manual cluster merge
→ vmap-based named part export
→ quality report
→ face coverage report
```

## Final v2 merge

```text
screen: [3, 4]
keyboard_base: [2]
hinge: [1]
residual_uncertain: [0, 5]
```

## Key validation result

```text
source faces: 30000
merged faces with duplicates: 31296
unique selected faces: 30000
unique_face_coverage_ratio: 1.0
duplicate_boundary_faces: 1296
duplicate_ratio_over_selected: 0.0414
bbox_size_ratio: [1.0000, 1.0000, 1.0000]
```

## Interpretation

The v2 merge preserves the full low30k object geometry. The duplicate faces are small boundary overlaps caused by the vmap face-selection rule.

## Judgment

```text
Gate A PartField inference: PASS
Gate A clustering: PASS
Gate A vmap merge: PASS
Gate A geometry preservation: PASS
Gate A semantic part quality: PROVISIONAL PASS
```

This result is strong enough to start Gate B contact proposal. However, the semantic labels are still manual part proposals, not ground-truth part segmentation.

## Next step

Proceed to Gate B:

```text
manual / MLLM finger-part contact proposal
```

Do not start optimization until Gate C verifies the contact proposals with 3D geometry, depth, and projection checks.
