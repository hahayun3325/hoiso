# Gate A — aket01 PartField vmap merge observations

## Status

This run verifies the PartField-enabled Gate A pipeline on `aket01`.

The completed pipeline is:

```text
low30k object mesh
→ PartField inference
→ PartField over-clustering
→ manual cluster merge
→ vmap-based named part export
→ coordinate-consistent quality report
````

## Why vmap-based export is better

The earlier merge used exported cluster `.ply` files. That caused a coordinate-frame mismatch when compared with the original `selector_v41` mesh.

The vmap-based adapter uses:

```text
input_mesh_low30k/00000.obj
+
00000_part_i_vmap.npy
```

This preserves the coordinate frame of the low30k source mesh and makes the quality report meaningful.

## v2-vmap observation

Merge file:

```text
aket01_cluster_merge_manual_v2.json
```

Parts:

```text
body: [0, 1, 4]
top_or_cap: [5]
noise_or_uncertain: [2, 3]
```

The body is usable and preserves most object mass. The `top_or_cap` part is weak and fragmented.

Quality report:

```text
source faces: 30000
merged faces: 23662
face coverage ratio: 0.7887
bbox ratio: [0.8938, 0.9699, 0.7994]
```

Interpretation:

```text
v2-vmap is good for semantic contact reasoning, but it drops too much residual geometry for final no-regression evaluation.
```

## v3-vmap observation

Merge file:

```text
aket01_cluster_merge_manual_v3_geometry_preserving.json
```

Parts:

```text
body: [0, 1, 4]
top_or_cap: [5]
residual_uncertain: [2, 3]
```

The body is usable. The `top_or_cap` part is still weak and fragmented. The `residual_uncertain` part contains scattered fragments, but it helps preserve object geometry.

Interpretation:

```text
v3-vmap should be used for Gate A geometry-preserving no-regression evaluation.
v2-vmap should be used for cleaner semantic/contact reasoning.
```

## Final judgment

This is a successful Gate A smoke test, but not a final clean semantic part reconstruction.

It proves:

```text
PartField can run on the reconstructed object.
PartField can over-cluster the object mesh.
Manual merge can produce named part files.
The body part is recoverable.
The vmap adapter fixes the coordinate-frame issue.
```

It does not yet prove:

```text
clean cap/neck separation
paper-quality part reconstruction
final Gate A no-regression against ground truth
```

