# Spatial hand–object distance diagnostics

The portable diagnostic workspace is now connected to a per-vertex surface-distance module. Previously, parent code could inspect a candidate and its global gap. It can now locate which parts of the hand are close to the object and inspect each nearest-triangle witness. All four saved candidates remain unchanged and unaccepted.

`hand_object_distances.build` authenticates a private snapshot of the H2 workspace using its separately supplied checksum and existing pipeline verification. It uses every object triangle and every hand vertex. A deterministic AABB tree accelerates the nearest-surface search. Each result stores the hand vertex index, object triangle index, closest point, barycentric weights, unsigned distance and distance divided by the object's bounding-box diagonal. No provenance transform is reapplied.

The offline HTML provides candidate selection, rotation, hand focus, a display threshold and clickable witnesses. Object points are sampled only for display. White lines join the inspected hand vertex to its nearest point on the full object surface. Thresholds control colors and counts; they are not scientific acceptance criteria. Downloading JSON preserves all four candidates and witnesses.

## Scientific limits

- These are unsigned, vertex-sampled distances. They do not measure penetration depth, certify physical contact, or describe a continuous area-weighted hand surface.
- The separate saved triangle-surface minimum may be lower than every vertex distance. Existing collision gates are preserved. In particular, the minimum-scale candidate remains blocked for transverse crossings.
- Scene units follow unverified MoGe scale. Bounding-box normalization removes a shared uniform scale factor but does not establish metric accuracy or anatomy.
- The completed human visual review remains preserved. A separate manual reference is still pending for quantitative mask validation. No findings or reference data are generated here.
- Scale, geometric accuracy, physical contact, parent acceptance and placement remain unresolved. No candidate is selected automatically.

## Run from the repository

```bash
python3 -I -S -B tools/tracehoi/measure_hand_object_distances.py build \
  --workspace /path/to/extracted/H2/workspace \
  --workspace-sha256 16171d47ef228fca3b4bb7ffe84911c9677d4672c2ff7c6d2cd835b985047083 \
  --case alapuse02v3n60 --purpose hand_object_distances \
  --output /path/to/new/distance-output
```

The output must be new. Keep the printed receipt checksum. `verify` uses the same arguments plus `--receipt-sha256` and recomputes the complete result against the authenticated workspace. Placement purpose is refused.

## Validation and delivery

Tests cover analytical plane/edge/vertex cases, degenerate triangles, rigid transforms, uniform scaling, finite bounds, deterministic ties, search-budget refusal, exhaustive search comparisons and immutable input handling. Real-data checks reconstruct all 3,112 witnesses and compare the three original candidates with the earlier independent NumPy surface audit. Published-source tests and a CLI rebuild comparison run before and after installation.

The J3 manual carrier adds exactly the module, CLI, test runner, tests and this note on top of H2 commit `71814f6c98898aeccd2ac7b1865d8aff04135bab`. It uses a normal push after verifying the recorded local and remote branch. It performs no model call, fitting, GPU work, dependency installation or mask edit. Server collection preserves the new viewer, numerical packet and original H2 workspace.

After verified publication and replacement evidence, the carrier archives the complete H2 working tree and moves that exact tree to Linux Trash. Original terminals, complete evidence archives, user review/reference JSON, original images/masks, source geometry and checkpoints must be retained. Keep all partial J3 outputs if any stage fails; do not rerun the same attempt.
