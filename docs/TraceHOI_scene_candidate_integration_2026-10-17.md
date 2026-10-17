# TraceHOI diagnostic scene integration — 2026-10-17

The saved-input pipeline now exposes four hand/object scene candidates through a repository reader and CLI. The reader verifies case identity, the supplied manifest digest, asset hashes, evidence consistency, camera axes, and mesh layout before returning mesh bytes. It uses only the Python standard library. This integration preserves the U5 reader bytes and adds repository entry points and reproducible synthetic contract tests.

## Recorded progress

The single case `alapuse02v3n60` has a generated Hunyuan object, a selected-right-hand HaMeR prediction, independent ViTPose targets, and a provisional SAM2 mask revision. Fresh MoGe observation N7 and CPU fitting P8 supplied the revised scene camera and geometry. These are learned or fitted estimates, not independent geometric ground truth.

Q9 assembled three diagnostic scenes. R2 measured triangle-surface proximity; S3 found 166 transverse crossing pairs in the minimum-scale branch. T4 refined that branch's scale from 2.191355141170339 to 2.2025070784651954 while keeping its projected joints fixed. The refined surface gap was 0.00011368397979591937 in unverified MoGe scene units. U5 packaged all four branches and verified four diagnostic loads and four placement refusals.

No candidate is accepted. Mask accuracy, metric scale, geometric accuracy, and physical contact remain unresolved. Surface separation alone is not a placement acceptance criterion. The sensitivity range is not a confidence interval. This change does not run a model, optimize geometry, or route candidates into the default production pipeline.

## Entry points

From the repository root, using Python 3.10 or newer:

```bash
python3 -I -S -B tools/tracehoi/check_scene_candidates.py
python3 -I -S -B tools/tracehoi/inspect_scene_candidates.py \
  /absolute/path/to/handoff/scene.json \
  --sha256 65a187a301e7888ea7102bd8d41e609ff11fb98c293061e6b8e4c194fe7640bb \
  --case alapuse02v3n60 --candidate minimum_scale_refined --purpose diagnostic
```

Use the digest from an authenticated receipt; do not calculate a new digest merely to accept a changed manifest. Keep the manifest's `assets/` and `evidence/` directories beside it. The CLI loads the repository module by file path to avoid importing unrelated model initialization code.

The API is `load_candidate(manifest_path, expected_sha256=..., expected_case_id=..., candidate_id=..., purpose=...)`. It returns immutable verified mesh bytes, camera intrinsics, frame conversion, identity mesh model matrices, and diagnostic blockers. All meshes already contain their scene transforms. The `source_to_scene_provenance_only` matrices must not be applied again.

The scene frame is x-right, y-up, z-backward; the camera frame is x-right, y-down, z-forward. The conversion is diag(1,-1,-1,1). Version 1 is scoped to this four-candidate, 512×512 saved-scene contract. It is not a general production-scene schema. Every `--purpose placement` request fails; the crossing branch stays available for diagnosis.

## Validation and retention

The repository test suite uses synthetic triangles, images, and evidence. It requires no checkpoints or case assets. The integration command also exercises the installed repository CLI on the authenticated real U5 bundle, checks all four asset bindings, and verifies all four placement refusals. Normal Git hooks are retained. The script commits only the seven named additions and verifies their contents and the remote branch head.

The case bundle remains outside Git. After successful publication, the full U5 tree is archived with hashes and readback before its working directory moves to recoverable Trash. Preserve original terminal logs, complete evidence archives, original images/masks and model assets, current partial outputs, and repository notes and sources. Do not rerun used attempt scripts or empty Trash during this work.

Next research work is to review the provisional hand mask and independent targets, establish a defensible scale/placement acceptance rule, and connect an explicitly accepted scene to downstream interaction stages. This diagnostic reader makes that boundary testable; it does not bypass it.
