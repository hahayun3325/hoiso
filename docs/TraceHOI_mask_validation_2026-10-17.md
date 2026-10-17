# TraceHOI: separate reference mask validation

F8d5Vm2F follows E7 commit `04b50be6db38a997fafd92d971b51cb21e650ff8`. E7 recorded Fred Cui's completed `visually_consistent` observation and preserved all four diagnostic scenes. This step implements the next validation design; the user's visual review is not repeated or overwritten.

## Evaluation contract

The protocol freezes the exact original 512 × 512 RGB, selected hand identity, reviewed hand-only mask, ambiguous overlap mask, source package and completed human review. The question is agreement between that hand-only support and a separately drawn visible-hand reference. The proposed annotation scope is the selected lower/right hand through the wrist crease, excluding the upper hand, object and forearm. Uncertain wrist and occlusion boundaries are explicitly ignored. This anatomical scope is a validation design, not a claim that the existing broader support is wrong.

The separate offline annotation page contains only RGB, identity and protocol context, without candidate-mask pixels or model silhouettes. Polygons and brush edits label 255 as visible selected hand, 0 as background and 128 as uncertain/unlabelled. All pixels start uncertain. Background fill explicitly replaces every uncertain pixel and is undoable; use it before preserving uncertain boundaries. Drafts can be saved and resumed. Completed references require an annotator, time, notes, whole-image inspection and declarations against tracing the candidate or using model-assisted segmentation. Prior exposure to the candidate must be recorded honestly. These declarations are self-reported; the system does not verify authorship or blinding.

The scorer excludes the fixed 289 ambiguous overlap pixels and any reference uncertainty. It reports TP, FP, FN, TN, IoU, Dice, precision, recall and evaluated coverage together. Zero-denominator ratios are null. Coverage and the reference's uncertainty remain visible so sparse annotation cannot masquerade as full-image evaluation. No acceptance threshold is selected. A single self-reported reference and image do not establish dataset accuracy, geometry, metric scale, physical contact or placement.

No independent reference was supplied for F8. Therefore `status` remains `awaiting_reference`, `metrics` is null and every accuracy/placement acceptance flag remains false. The actual user review remains complete. No new labels, observations or scientific findings are fabricated.

## API and CLI

`src/foho/geometry/mask_validation.py` exposes deterministic `build` and `verify` functions over the authenticated reviewed portable package. Optional reference JSON is preserved byte-for-byte. Draft, mismatched-image/protocol, malformed, model-assisted or candidate-traced records are refused. Output files are immutable and have a readback receipt. Verification rebuilds the outputs and checks the existing scene package again. Source masks, geometry and human review stay unchanged.

Run `tools/tracehoi/validate_hand_mask.py build --package <reviewed-scenes-folder> --package-sha256 <package.json SHA-256> --case alapuse02v3n60 --purpose mask_validation --output <new-folder>` to prepare the pending protocol and UI. Add `--reference <completed-reference.json>` to score a separately supplied record. `verify` takes the same source inputs plus `--receipt-sha256 <files.json SHA-256>` and checks the embedded reference. New output folders are required. The HTML is a local workspace; server validation is authoritative for file and context consistency.

## Validation and retention

Thirty unit checks cover known confusion counts, exclusion unions, undefined ratios, malformed bindings and provenance, draft rejection, and RGB-only annotation payloads. Publication also runs the existing record/readiness/export/intake suites and real-package round trips before and after installing five exact additions. Tests use synthetic reference labels; no synthetic reference is delivered as human evidence.

Only after normal push verification and replacement evidence does F8 archive and Trash the complete E7 working folder. The complete archive, original terminal, exact user review and current F8 outputs are retained. A compact transfer ZIP is not a full working-tree backup. No model, GPU, optimization, mask mutation or placement commitment occurs.
