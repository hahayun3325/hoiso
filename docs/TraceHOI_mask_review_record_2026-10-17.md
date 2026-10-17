# TraceHOI: bound human mask-review records

Y9 published the offline hand-domain viewer at `9e8c8215d462791be023c335494bbc490ac74c25`. The returned ZIP, terminal, source files, review report and HTML were authenticated before this extension was prepared. All four scenes remain diagnostic and unaccepted.

The remaining mask-review task needs an explicit observation of the original image and provisional mask. This addition provides a direct hand-only mask overlay, rectangle annotations, reviewer summary, draft/resume JSON and a completed-review export. The existing comparison, zoom, boundary and residual tools remain available. No observation is filled in on the user's behalf.

The JSON record binds the exact scene manifest, Y9 review, audit and every source asset, including the original image and provisional mask. An offline CLI verifies those bindings against the authenticated scene and saved review. It rejects changed evidence, duplicate JSON keys, nonfinite values, unknown fields, invalid rectangles, incomplete inspection declarations and attempted geometry acceptance. A review that requests mask revision must locate at least one region. Notes are plain text and are rendered with `textContent`.

`human_review_record_complete` means only that a human-supplied record is structurally complete. Reviewer identity is self-reported. Neither the UI nor validator certifies mask accuracy, clears `mask_review_required`, identifies scale, selects a candidate, verifies contact or admits pipeline placement. A later, separately reviewed revision can consume the returned record. The current original mask and all three raw SAM2 candidates stay preserved. The direct view uses the 6,934-pixel hand-only support; 289 ambiguous hand/object-overlap pixels remain excluded. The wrist partition remains a heuristic, not an anatomical label.

## Usage

Run `tools/tracehoi/mask_review_record.py build SCENE --sha256 SCENE_SHA --case alapuse02v3n60 --review-dir SAVED_Y9_REVIEW --files-sha256 REVIEW_RECEIPT_SHA --output NEW_DIRECTORY` with the hashes supplied by the authenticated bundle. Open the generated `index.html`. Review the original image and mask, draw or enter regions, enter a summary, and download a draft or completed JSON record. The HTML has no network dependencies and does not persist edits until downloaded.

To validate a returned record, use the same evidence arguments with `validate` instead of `build`, and `--record RECORD.json --require-reviewed` instead of `--output`. Omitting `--require-reviewed` permits drafts for inspection. Validation writes no pipeline input, mask or acceptance state. The command prints a receipt containing both the input-file hash and the canonical-record hash.

## Publication and retention

The Z2 manual-transfer runner requires the recorded Y9 local and remote head, tests the candidate and installed code, adds only these five source/test/documentation files, commits and pushes normally. Only after verified publication and a replacement archive may it archive, read back and Trash the exact Y9 working tree. Original terminal guards, retained archives, source images/masks, T4/MoGe/preprocessing inputs, model assets, repository notes and current partial outputs remain protected.

No model inference, GPU work, optimization, mask editing or placement acceptance is performed by this step.
