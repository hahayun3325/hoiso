# TraceHOI portable diagnostic pipeline — 2026-10-17

G9 published candidate comparison at `851f03df3a895d1ded297d99efb3952c537d57da`. The complete human visual review is retained. Separate-reference validation remains pending, and scale, contact and placement remain unaccepted.

## Connected stages

The new `diagnostic_pipeline` module composes the authenticated scene export, mask validation and candidate comparison in a self-contained workspace. It retains all four source meshes, cameras, original evidence and exact human review bytes. The workspace contains a source scene, validation output, comparison output, a stage report and an offline interactive dashboard. Its manifest binds every file. Verification rebuilds the derived stages and compares their bytes, so changing both a report and its local checksum is insufficient to pass verification against the separately recorded manifest hash.

The parent interface requires an explicit candidate ID and diagnostic purpose. It returns exact immutable mesh bytes, camera data and identity model matrices. Meshes already contain scene transforms; provenance transforms must not be applied again. A crossing candidate can be inspected diagnostically but cannot be accepted for placement through this interface. No automatic winner is selected.

## Reusable commands

Run from the repository using the recorded Python environment. Use a new output directory for each build. Replace the paths and digest values with the intended package and its separately recorded checksum.

```bash
python tools/tracehoi/run_diagnostic_pipeline.py build \
  --package /path/to/source_scene --package-sha256 SOURCE_PACKAGE_SHA256 \
  --case alapuse02v3n60 --workspace /path/to/new_workspace \
  --purpose diagnostic_pipeline
```

The build prints the verified workspace receipt, including its SHA-256. Preserve it separately.

```bash
python tools/tracehoi/run_diagnostic_pipeline.py verify \
  --workspace /path/to/workspace --workspace-sha256 WORKSPACE_SHA256 \
  --case alapuse02v3n60 --purpose diagnostic_pipeline
python tools/tracehoi/run_diagnostic_pipeline.py inspect \
  --workspace /path/to/workspace --workspace-sha256 WORKSPACE_SHA256 \
  --case alapuse02v3n60 --candidate minimum_scale_refined \
  --purpose diagnostic_pipeline
```

`inspect` prints mesh bindings and metadata; Python callers receive mesh bytes from `load_candidate`. Placement purpose is refused. Building with a later `--reference /path/to/reference.json` uses the same frozen protocol, strictly validates the original reference bytes and scores them without inferring accuracy or approval. A missing reference remains pending; invalid supplied records fail before publication. The original visual-review JSON is a different record and must not be substituted for the reference.

## Portable inspection

Extract the entire workspace ZIP and open `index.html`. The top-level dashboard connects the scene viewer, validation view and RGB-only reference annotator; its candidate and profile controls only change the display. The exact historical comparison HTML remains under `comparison/`, including its old standalone links; use the top-level dashboard for portable navigation. The server collector also provides linked standalone HTML files. Keep them together.

## Validation and boundaries

Contract tests cover stage identity joins, missing/scored reference behavior, explicit candidate loading, placement refusal, immutable source bytes, symlink/count bounds and HTML escaping. Real-bundle validation checks reproducibility, relocation, exact mesh bytes, identity transforms and tamper refusal. Integration tests exercise normal publication and reversible cleanup, missing inputs, failed push and unexpected files.

This addition does not execute models, fitting, GPU work or scene registration. It does not alter masks or establish independent metric scale, 3D accuracy or physical contact. The four candidates and all scientific acceptance flags remain unchanged.

## Retention and publication

The H2 manual carrier verifies the returned G9 ZIP and terminal, the recorded clean Git base and all 53 existing source files. It installs only these five additions, runs candidate and installed tests, commits and pushes normally. After verified publication it archives and moves only the exact completed G9 working tree to Trash. Original terminal logs, inputs, human/reference records and evidence archives are retained. Unexpected files stop cleanup and remain in place. Never remove the current run folder, its terminal guard or the only evidence copy to save space.
