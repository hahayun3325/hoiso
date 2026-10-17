# TraceHOI visual scene review — 2026-10-17

The diagnostic reader published in `1fe1049a92b2d7f45635317cf0c49b54b0564fa2` now has an offline visual consumer. It produces original-image overlays, visible-hand and object mask comparisons, projected depth ordering, a numerical JSON report, and a self-contained HTML viewer for all four saved candidates.

The renderer uses the verified reader's saved camera and meshes. Source-to-scene provenance transforms are never reapplied. A standard-library CPU rasterizer evaluates two-sided triangles at integer pixel centers with perspective-correct depth. It bounds image dimensions, faces, vertices and pixel work, and rejects meshes crossing the camera plane. The CLI runs on Linux with a 120 CPU-second / 2 GiB address-space budget; the delivery wrapper adds a wall-time bound.

From the repository root:

```bash
python3 -I -S -B tools/tracehoi/check_scene_candidates.py
python3 -I -S -B tools/tracehoi/check_scene_visual_review.py
python3 -I -S -B tools/tracehoi/render_scene_review.py \
  /absolute/path/to/handoff/scene.json \
  --sha256 65a187a301e7888ea7102bd8d41e609ff11fb98c293061e6b8e4c194fe7640bb \
  --case alapuse02v3n60 --output /absolute/path/to/new-review-folder
```

Open `index.html` locally. Switch the viewing candidate and layer; opacity and synchronized zoom help compare the original RGB with diagnostic overlays. The JSON download records exact inputs, image/mesh bindings, mask agreement and pixel ordering. The output folder must be new. No server, browser network access, model package or GPU is needed to view the report.

Hand comparisons use the provisional **hand-only** mask; the 289 ambiguous hand/object overlap pixels remain separately marked and excluded from both fitting supports. IoU measures agreement with that provisional mask, not geometric accuracy. Object-only mask agreement is likewise diagnostic. Small hand/object depth overlaps may be hard to see until zooming; colors do not establish collision or contact.

All four candidates remain unaccepted. The minimum-scale branch retains its recorded transverse-crossing blocker. The refined branch retains unresolved mask, scale, geometric-accuracy and contact blockers despite numerical surface separation. Conditional scales, source meshes, masks, source images and the default pipeline placement are unchanged.

Tests cover camera axes, integer centers, reciprocal-depth interpolation, two-sided rendering, nearest surfaces, scale/projection invariance, depth ordering, invalid geometry, bounded work, image integrity, and report isolation. The delivery script renders the actual verified V6 scene before and after repository installation, compares outputs byte-for-byte, and checks the first three branches against saved Q9 pixel counts. It publishes only source/tests/docs; case images and scene artifacts remain outside Git.

The next decision is a visual review of the provisional hand mask and systematic geometry mismatch, followed by a justified scale/placement acceptance rule. This report supports that review and provides no automatic acceptance action.
