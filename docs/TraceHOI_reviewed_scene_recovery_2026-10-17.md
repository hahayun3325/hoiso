# TraceHOI: completed visual mask review and recovered scene handoff

Case: `alapuse02v3n60`. Checkpoint: `E7c4Ul9E`, 2026-10-17.

Fred Cui completed the observation review at `2026-10-17T22:09:20Z`, marked both the original image and provisional mask inspected, and chose `visually_consistent`. The notes state that the provisional mask covers the desired hand and that development should proceed. The original JSON has 3,628 bytes and SHA-256 `5b898771748bdb287d47ed2e7d90313e4dcd41796341badbabe0584a6c321c83`. It is preserved verbatim in the server evidence and portable handoff; the JSON is not added to Git.

The preceding C5 run correctly reported a missing record: the completed file was on the Mac rather than in the server input location. E7 imports that exact record using the already published C5 API. This completes the human visual review requirement. It does not create a new segmentation or repeat any model inference.

D6 stopped before any Git operation because its required C5 ZIP was absent from server Downloads. Its return archive and terminal authenticate that failure. E7 is a new attempt, using one hash-bound transfer bundle containing the exact C5 archive/terminal, the failed D6 archive/terminal, and the human JSON. Server Downloads is no longer an input dependency. The transfer bundle and original terminals remain retained for recovery.

The review names a rectangle in its prose, but contains no serialized finding regions (`findings: []`). No rectangle, missing annotation, or revision request is inferred. A `visually_consistent` record with no findings is valid. The provisional mask is now visually approved by the user for continued diagnostic development. This is distinct from independently measured segmentation accuracy.

## Preserved geometry and scope

All four saved candidates remain in the reviewed portable package: primary, minimum scale, maximum scale, and the collision-refined minimum-scale branch. The source images, mask pixels, meshes, transforms, source review, and scene resource hashes are unchanged. Geometry is already in scene coordinates and must not receive its provenance transforms again.

The human record retains `mask_accuracy_verified: false`, `scale_identified: false`, `physical_contact_verified: false`, and `placement_ready: false`. No candidate is selected and no metric scale is accepted. The minimum-scale candidate still has the recorded transverse crossings. Numerical clearance in the refined candidate is not evidence of physical contact. Historical source-manifest mask-review flags describe the earlier snapshot; the new intake/readiness record separately reports the completed review.

## Next development boundary

The published readiness API now returns `review_state: reviewed`, `human_review_record_complete: true`, and `next_action: design_independent_mask_validation`. No mask revision is requested or applied.

The next validation design should freeze this image/mask binding and define which question is being tested before fitting another pose or scale. A quantitative segmentation-accuracy claim requires a separately produced reference mask with documented provenance and an occlusion/hand-object-overlap policy. The current SAM2 mask, HaMeR silhouette, and MoGe support are not interchangeable with independent ground truth. Record any such future reference separately; do not overwrite this accepted working branch. The current 289 ambiguous overlap pixels remain excluded from hand-only support.

Existing scene candidates can continue to be inspected and compared as diagnostics. New optimization must declare its objective and evaluation evidence and retain the current candidates as baselines. Final placement still requires resolving scale, geometry, collision, and contact questions; this visual review alone supplies none of those measurements.

## Validation and retention

E7 verifies the C5 return ZIP and original terminal, all 42 published source-file hashes, the exact human record and context, portable-package readback, preservation of every source asset, inherited-record intake, and placement refusal. It runs the existing 24 record, 26 readiness, 24 export, and 22 intake tests before and after adding this note. The local and remote repository must both start at C5 commit `66cb25c610a1bf6d7fb2d2b84aa28c337e50c5f1`. Only this note is staged and normally pushed; no existing code or raw human record is changed.

After verified publication and replacement evidence, E7 archives and moves only the failed D6 and superseded C5 working folders to Linux Trash. It verifies every expected file before moving a present folder. If a folder is already absent, it explicitly records that fact and retains its authenticated return ZIP and terminal; it does not claim recovery of unknown deleted files or a complete-tree archive. Original terminals, the exact human JSON, transfer bundle, model assets, original inputs, full evidence archives, and the new E7 folder remain. Do not empty either Trash or delete the remaining evidence as part of this step. If any source has changed or an operation fails, retain partial outputs and investigate rather than rerunning the attempt.
