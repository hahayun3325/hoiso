# TraceHOI hand model-domain audit — 2026-10-17

W7 published the offline scene reviewer at `7b804ca1bd98d8053503f55ae76be7e13685ddcb`. Four saved scene candidates remain diagnostic. None has an accepted scale, verified physical contact or committed pipeline placement.

The saved HaMeR mesh ends at an open wrist boundary, whereas the provisional selected-hand mask includes pixels farther along the forearm. This addition measures that difference separately from residual mismatch on the hand-facing side. It uses the original RGB crop and unchanged saved geometry, camera and hand-only mask; it performs no inference, fitting or mask edit.

## Method and limits

The audit requires a single simple boundary loop and rejects nonmanifold edges, duplicate faces, multiple loops and ambiguous projected orientations. It projects the boundary with the recorded scene-to-camera convention, builds a principal-axis band containing every boundary vertex plus a fixed two-pixel margin, and orients it toward the projected mesh centroid. Pixels are partitioned into the hand-facing side, boundary band and beyond-boundary side. The partition is a heuristic model-domain diagnostic, not an anatomical label or ground truth.

Visibility is computed by the W7 two-sided CPU rasterizer and saved depth tolerance. Full-mask scores reproduce W7 exactly. Region counts sum back to full counts. Connected components identify residual mask-only regions without changing the mask. A region-restricted IoU must not replace the full score or determine candidate acceptance.

## Saved-case findings

For `alapuse02v3n60`, all four meshes have 16 open-boundary vertices. Of 6,934 hand-only mask pixels, 1,579–1,825 lie beyond the projected boundary band, and none of those pixels is covered by the projected hand mesh. A further 1,023–1,411 mask pixels on the hand-facing side remain uncovered. The forearm coverage difference therefore explains only part of the mismatch.

| Candidate | Full visible-hand IoU | Hand-side IoU | Beyond-boundary mask pixels | Hand-side mask-only pixels |
|---|---:|---:|---:|---:|
| primary | 0.4946 | 0.6690 | 1797 | 1326 |
| minimum_scale | 0.4865 | 0.6645 | 1825 | 1411 |
| maximum_scale | 0.5568 | 0.7193 | 1579 | 1023 |
| minimum_scale_refined | 0.4865 | 0.6645 | 1825 | 1411 |

These are mask-agreement diagnostics, not accuracy estimates or a ranking of valid placements. Minimum-scale and refined candidates have the same image mask despite different saved collision findings. The minimum-scale branch retains its transverse-crossing rejection. Scale, contact, mask review and geometric validation remain unresolved.

## Run against a verified portable scene bundle

```bash
python -I -S -B tools/tracehoi/check_hand_domain_audit.py
python -I -S -B tools/tracehoi/audit_hand_domain.py /path/to/scene.json \
  --sha256 VERIFIED_MANIFEST_SHA256 --case alapuse02v3n60 --output /new/output/directory
```

The output directory must not exist. The tool writes a JSON audit, Markdown report, four annotated PNGs and a file-binding receipt. It uses only the Python standard library; on Linux its CLI limits address space to 2 GiB and CPU time to 120 seconds. The server runner adds a 60-second subprocess wall timeout.

The X8 deployment authenticates W7, checks 12 existing repository files, runs 27 reader, 22 renderer and 21 domain tests, compares real saved inputs before and after installation, and adds exactly this note, the module, two tools and tests. Case imagery and model assets are not committed. Publication and cleanup results are recorded in the return packet.

The W7 HTML transfer failure was a collector bug: a 4,851,791-byte HTML was given the 1 MiB terminal cap. X8 preserves that exact HTML and uses an explicit 8 MiB visual-review cap with its recorded hash. The original W7 result remains valid.

Next scientific work should address the remaining palm/finger mismatch and independent geometric validation. This diagnostic does not automatically crop or accept the mask, select a candidate or authorize placement.
