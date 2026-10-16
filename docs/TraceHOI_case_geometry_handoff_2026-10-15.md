# TraceHOI case-to-geometry handoff — 2026-10-15

Development resumed after checkpoint `1315d8193505df42581870337ca86caa9c9fec04` was published to `phase-2.1-agile-vlm-upstream-gate`. The checkpoint receipt verified the remote commit and clean working tree. Its twelve obsolete Downloads copies were already absent; the restore attempt moved no server files to Trash and restored the missing original checkpoint terminal.

This increment fixes three concrete geometry handoff problems: first-underscore case truncation, ambiguous Hunyuan image/result association, and MoGe export functions shadowing the requested output flags.

## Filename and stage contract

The shared `foho.case_artifacts` helper removes only reserved trailing artifact suffixes. It preserves underscores and embedded `hoi` in case names. For example:

| Stage input | Expected output |
| --- | --- |
| `hoi_case_07_cropped_hoi_wo_bckg_0.png` into MoGe | `hoi_case_07_cropped_hoi/pointcloud.ply` with default flags |
| `hoi_case_07_occ_obj.png` into Hunyuan | `hoi_case_07_hoi_mesh.ply` |
| That mesh plus the corresponding MoGe directory into H2M | transform prefix `hoi_case_07_hoi_mesh` |

Recognized image suffixes: `_occ_obj`, `_cropped_hoi`, and `_cropped_hoi_wo_bckg`, with optional `0`, `1`, `True` or `False` hand flag on the cropped forms. Plain image stems are also supported. Those suffixes are reserved; they cannot distinguish a literal case name ending in the same suffix. Multiple images mapping to one destination fail before native imports or model loading. Select one view upstream.

The foundation manifest continues to send the object-only image to Hunyuan and the joint scene image to MoGe. This patch does not alter that manifest, main-pipeline routing, preprocessing, hand selection, MANO, VLM prompts or guidance.

## Wrapper behavior

- Hunyuan sorts input filenames, processes one case per call, and requires exactly one non-null mesh result before export. The captured installed flow-matching source accepts a single PIL image; its `multi_view` parameter is unused. The wrapper now passes `False` explicitly. This is a case-association correction, not evidence that the previous parameter fused views.
- Existing nonempty mesh files retain the previous skip behavior. They are not revalidated for provenance or mesh quality. Empty files, directories and symlink destinations are rejected. Exports use a uniquely named `.partial.ply` and an exclusive final link, so a failed export does not become a reusable final mesh and a competing output is not overwritten. Partial exports are retained for diagnosis.
- MoGe writer aliases preserve the `save_maps`, `save_glb` and `save_ply` booleans. Output directories remain confined to the declared root, including when the parent directory contains `hoi`. Input subdirectories are preserved, and destination collisions fail before inference.
- H2M preflights every recognized Hunyuan mesh and its MoGe target before importing the aligner. Missing or empty files fail the batch instead of silently skipping cases. Target preference remains `mesh.ply`, `pointcloud.ply`, then `mesh.glb`; transform names and alignment settings are unchanged.

Hunyuan and H2M still consume flat directories. MoGe's existing recursive-directory support does not imply recursive end-to-end pairing. Case IDs already truncated by an upstream stage cannot be recovered here. Full pipeline support for arbitrary case IDs remains a separate task.

## Validation and remaining limits

Run `python3 -I -S -B tools/tracehoi/check_case_handoff.py` from any directory. Tests exercise actual wrapper functions with small native-library and model substitutes: per-case routing, result-count mismatch, export failure/concurrent output, file ordering, H2M missing-case admission, path confinement and export flag selection. The existing two MoGe path regressions also run when present.

These are source and fixture tests. They do not load weights, execute real inference, validate geometric quality, contact the service manager, or prove full parent acceptance. Single-case Hunyuan calls also change batch-dependent random-number behavior and throughput; output equivalence to a previous five-image batch is not claimed.

M6 native imports previously passed. N7 CPU loading did not launch its service. P8 then stopped on `pinned_busctl_changed` before manager contact, model construction or weight loading. Native CPU construction, strict checkpoint loading, GPU inference and full TraceHOI acceptance remain unverified. Historical executable pins must not be silently replaced to bypass that failure.

The next runtime milestone is a newly named, bounded CPU construction/checkpoint-load attempt with an explicitly verified current tool identity, followed by a single-case geometry integration check. Do not rerun N7 or P8. Keep source fixture validation and model execution outcomes distinct.

## Preserve these records

Keep `.git`, repository source/config/tests/tools, the historical pause note, `TraceHOI_progress_and_resumption_2026-10-15.md`, this note, and `TraceHOI_WACV2027_reviews_and_next_steps_2026-10-15.md`. Keep original attempt directories, home-level terminal logs, input bundles, models and data. Terminal logs are execution evidence and run-once guards. The missing original checkpoint terminal—not an obsolete note—caused the earlier recovery failure.

Only explicitly listed, hash-matching transfer duplicates with verified retained originals may go to Trash. Never bulk-delete `tracehoi-*`, `*.terminal.txt`, `docs/`, or `tools/tracehoi/checkpoints/`.
