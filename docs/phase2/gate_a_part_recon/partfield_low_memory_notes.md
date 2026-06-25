# Gate A PartField Low-Memory Notes

During Phase 2 Step 1 Gate A, PartField inference initially failed on `aket01` because the original `selector_v41` object mesh was too large.

Original mesh:

```text
vertices: 117,580
faces: 234,374
````

The CUDA OOM happened during per-face point sampling inside PartField. The fix was to decimate the object mesh and reduce PartField sampling.

Successful low-memory setting:

```text
input mesh: input_mesh_low30k/00000.obj
vertices: 15,022
faces: 30,000
n_point_per_face: 1
n_sample_each: 10000
```

Successful PartField feature outputs:

```text
feat_pca_00000_0.ply
input_00000_0.ply
part_feat_00000_0_batch.npy
```

Successful clustering outputs:

```text
00000_part_0.ply ... 00000_part_5.ply
00000_part_0_vmap.npy ... 00000_part_5_vmap.npy
```

This is a PartField-enabled Gate A smoke test. It proves that PartField can run on the decimated `aket01` mesh and produce over-segmented candidate parts. It is not yet the final semantic part split.

Practical rule:

1. Start with 30k faces.
2. Use `n_point_per_face = 1`.
3. Use `n_sample_each = 10000`.
4. Only increase resolution after the full pipeline succeeds.
5. Do not run clustering before PartField feature files exist.
