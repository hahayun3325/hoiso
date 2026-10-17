# TraceHOI: explicit scene continuation contract

Z2 publication at `9e9a6ed1a0bd4e5bae03a0857f9c461d9687b42b` is verified from its returned archive and original terminal. All 163 member bindings, published sources, checks and review HTML were checked locally. Its output contains the review tool, not a completed human mask review. The new runner authenticates these same Z2 files on the server before repository writes. Local integration tests use the real saved evidence with temporary Git repositories and an explicitly synthetic auxiliary cleanup fixture; they never contact the server.

This addition exposes a parent-facing API that combines the diagnostic scene reader and bound human-review validator. `evaluate()` verifies the saved scene and review evidence and reports each stage's prerequisites. An absent record stays `missing`; a valid draft stays `draft`; an invalid supplied record fails rather than silently becoming missing. The original record's exact byte hash is retained alongside the canonical validation receipt. A completed review remains a self-reported observation, not a mask-accuracy certificate.

`prepare_stage()` supports diagnostic export of an explicitly named candidate, or revision-planning input from a completed review requesting revision. The latter returns the exact pixel regions and notes without modifying the mask. Placement always fails in this version. Clear surface separation cannot identify metric scale or prove physical contact. The minimum-scale crossing branch remains available for diagnosis and blocked for placement. No new model call or optimization occurs.

The offline readiness dashboard shows evidence availability, review state, stage prerequisites and all four preserved candidates. Changing a selector does not execute a stage. Its adjacent Z2 HTML supports completing the review. Downloaded records do not mutate the readiness snapshot; the CLI must validate them and regenerate a new snapshot.

## CLI

`tools/tracehoi/inspect_scene_readiness.py report SCENE --sha256 SCENE_SHA --case alapuse02v3n60 --review-dir SAVED_Y9_REVIEW --files-sha256 REVIEW_FILES_SHA --output NEW_DIR` generates the report, dashboard, adjacent mask-review HTML and file receipt. Add `--record RECORD.json` only for a real supplied record.

Use `prepare` instead of `report`, omit `--output`, and provide `--stage diagnostic_export --candidate primary` to inspect a diagnostic handoff. `--stage mask_revision_planning --record RECORD.json` requires a completed revision request. `--stage placement` is always refused. No prepared payload is automatically written into production state.

## Manual run and retention

The A3 runner checks local/remote Z2 heads, installs five exact additions, tests both candidate and installed sources, and pushes normally. It optionally snapshots `/home/fredcui/Downloads/tracehoi_mask_review_alapuse02v3n60_reviewed.json` if supplied. That record must match the current evidence; no review is fabricated or auto-completed. The original downloaded record is preserved.

Only after verified publication and replacement evidence does the runner archive, verify and Trash the exact Z2 working tree. Keep original terminals, archives, original masks/candidates/images and model assets, repository notes, current partials, and every user review record. The collector places the ZIP, terminal, readiness HTML and unchanged Z2 review HTML in server Downloads. No SSH connection is used from the Mac.
