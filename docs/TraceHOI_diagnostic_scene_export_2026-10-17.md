# TraceHOI: portable diagnostic scene export

A3 was published at `55ac7bd9b5e7ea9941a85f21f1b97006e71ba498`. Its 196-member return archive and original terminal were authenticated locally. Readiness is complete, but no completed human mask review was supplied. Placement, metric scale, geometric accuracy and physical contact remain unaccepted.

This step implements the diagnostic-export stage through the existing readiness API. Callers must specify the diagnostic purpose and candidate IDs. The output contains unchanged full-resolution hand/object PLY files, original source evidence, camera and coordinate conventions, the readiness report, optional original human-review bytes, the original review form and an offline geometry viewer. All original candidates and evidence remain in the package, including when callers request a display subset. The export candidate list is not a scientific selection; `selected_candidate` and `accepted_scale` remain null.

The verifier checks a separately supplied package-manifest SHA-256, exact file inventory and hashes, then rebuilds the expected package using the source reader and review validator. It rejects altered meshes, added files, symlinks, changed acceptance flags and modified preview content. A relocation check proves the package has no dependence on its original server working path. Integrity depends on the caller's supplied expected digest; it is not evidence of geometric accuracy.

The viewer uses 6,000 deterministic object vertices and the full hand wireframe. It is an orthographic inspection tool with candidate switching, front/side/top views, orbit controls, original RGB and exact PLY downloads. This sampled display has no occlusion, collision or contact certification. Full source meshes are retained byte for byte. They already contain their scene transforms; source transforms must not be applied again. Scene axes are x right, y up, z backward; the recorded scene-to-camera conversion flips y and z. No model, fitting or mask edits occur.

## CLI

Use `tools/tracehoi/export_diagnostic_scene.py build SCENE --sha256 SCENE_SHA --case alapuse02v3n60 --review-dir SAVED_REVIEW --files-sha256 REVIEW_FILES_SHA --purpose diagnostic --candidate primary --output NEW_DIRECTORY`. Repeat `--candidate` for each explicit candidate. A real review can be supplied with `--record RECORD.json`; missing review stays pending and invalid supplied records fail.

Use `verify PACKAGE_DIRECTORY --sha256 PACKAGE_JSON_SHA --case alapuse02v3n60 --purpose diagnostic` to authenticate a relocated export. Placement purpose is always refused. The supplied manifest digest must come from the expected receipt, not blindly from an untrusted package.

## Manual server run and retention

The B4 runner verifies the A3 return archive/terminal and local/remote repository base, runs 132 existing checks plus 24 export checks and real exports before and after installation, adds five exact files, commits and pushes normally. It exports all four diagnostic candidates. Server execution uses the Python standard library; no model service or GPU computation is launched.

After publication and replacement evidence are verified, only the exact A3 working folder is archived, read back and moved to Linux Trash. Original terminal guards, complete archives, source inputs, human review records and current partial outputs remain. A separate portable diagnostic ZIP, the run ZIP, terminal, orbit HTML and unchanged Z2 form are collected to Downloads for manual transfer. Do not rerun A3 or this B4 attempt.
