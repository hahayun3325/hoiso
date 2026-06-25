# Gate A — aket01 smoke conclusion

## Status

`aket01` passed the Gate A PartField plumbing smoke test.

The completed path is:

```text
selector_v41 object mesh
→ low30k decimation
→ PartField inference
→ PartField over-clustering
→ manual cluster merge
→ vmap-based named part export
→ coordinate-consistent quality report
→ face coverage / overlap report
````

## Key result

The geometry-preserving v3 merge uses:

```text
body: [0, 1, 4]
top_or_cap: [5]
residual_uncertain: [2, 3]
```

The v3 quality report shows:

```text
source faces: 30000
v3 selected faces with duplicates: 30256
unique selected faces: 30000
unique face coverage ratio: 1.0
duplicate boundary faces: 256
duplicate ratio over selected: 0.00846
```

## Interpretation

This means v3 preserves the full low30k source geometry. The extra 256 faces are small boundary overlaps caused by the vmap face-selection rule.

## Judgment

```text
Gate A smoke test: PASS
Semantic part quality: PARTIAL
Geometry preservation: PASS on low30k source
```

`aket01` is useful as a plumbing case, but it should not be the main evidence for articulated part reasoning. The next meaningful case is `alapuse01`, where the expected parts are screen, keyboard base, and hinge.
