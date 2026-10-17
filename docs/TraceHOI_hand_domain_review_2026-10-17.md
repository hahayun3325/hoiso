# TraceHOI interactive hand coverage review — 2026-10-17

The user-reported X8 run published commit `76f8649c37e6cfa6c4e8c86686e4373c0074fe1b` and completed cleanup. Its full return ZIP and original terminal are authenticated on the server before this deployment changes the repository. Local preparation uses the previously verified scene bundle and unchanged X8 audit code; local fixtures are not server evidence.

This addition connects the saved X8 audit to an offline interactive reviewer. It compares any two of the four diagnostic candidates, with synchronized zoom, overlay opacity, original-image and projected-boundary modes. Residual buttons highlight bounding boxes of the largest connected mask-only regions on the hand-facing side. Image clicks and keyboard-accessible numeric controls inspect the fixed boundary partition. The JSON download preserves all original audit facts.

The viewer does not change images, masks, geometry, camera, transforms or candidate acceptance. The principal-axis boundary band is a heuristic model-domain partition, not an anatomical label. The 1,579–1,825 mask pixels beyond the boundary explain only part of the mismatch; 1,023–1,411 hand-side mask pixels remain uncovered. Region-restricted IoU is not ground-truth accuracy or an automatic ranking. The minimum-scale crossing rejection remains visible. No scale or pipeline placement is accepted.

```bash
python -I -S -B tools/tracehoi/check_hand_domain_review.py
python -I -S -B tools/tracehoi/render_hand_domain_review.py /path/to/scene.json \
  --sha256 SCENE_SHA256 --case alapuse02v3n60 \
  --audit-dir /path/to/installed_audit --audit-sha256 AUDIT_SHA256 \
  --files-sha256 RECEIPT_SHA256 --output /new/output/directory
```

The tool authenticates the scene, audit JSON, receipt and all six audit outputs before building a self-contained HTML and JSON report. It uses only the Python standard library; no runtime network is needed. On Linux the CLI limits address space to 2 GiB and CPU time to 120 seconds. The deployment adds a 60-second wall timeout.

The deployment verifies 17 existing repository files, installs five exact additions, checks the existing contracts and new viewer checks, compares generated files before and after installation, and publishes normally. It then archives and moves only the verified X8 working tree to Trash, retaining original terminals and complete evidence archives. Source imagery and weights are not committed.

This review surface supports inspection of residual palm/finger mismatch. It does not substitute for independent geometric validation or provide an acceptance action.
