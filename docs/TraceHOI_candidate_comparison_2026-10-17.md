# TraceHOI saved candidate comparison — 2026-10-17

The four existing scene candidates remain unaccepted. This addition connects their saved projection, full visible-mask and triangle-surface diagnostics into one reproducible comparison API and offline viewer. It performs no fitting, inference or mesh transformation.

## Evidence and interpretation

- The separate human visual review is complete and says `visually_consistent`.
- F8 was published as `f846632cf0206101910fa8f8a36f8f05747a9c75`; its separate reference annotation is pending. Existing approval is retained; no second visual review is requested.
- The primary branch has the smallest median joint reprojection residual. The maximum-scale branch has the largest full visible-silhouette overlap with the working mask. The refined minimum-scale branch has the smallest positive recorded surface gap among branches without a recorded crossing.
- The original minimum-scale branch has recorded transverse crossings. It stays in the table and source package, but is excluded from diagnostic Pareto comparisons.
- `image_agreement` minimizes median reprojection residual and maximizes full visible-mask IoU. `image_and_proximity_hypothesis` additionally minimizes unsigned surface gap. The latter is an explicitly conditional proximity objective, not a contact observation.
- A branch is nondominated if no eligible branch is at least as good on all stated objectives and better on at least one. Comparisons use half-even rounding at six decimal places for pixel residuals and nine for IoU and gap. Raw values are preserved. These precisions are numerical conventions, not confidence bounds.
- Region-restricted mask scores are not used. Depth residuals are omitted because support subsets differ. Image fitting metrics are not held-out validation. Mask overlap is against the working mask, not the pending separate reference.

## API and commands

`candidate_comparison.build` authenticates the portable diagnostic package and the separate mask-validation packet, checks candidate/mesh/collision joins, and returns comparison JSON, offline HTML and a receipt. `verify` rebuilds the complete result from those same pinned inputs. `compare` is a pure diagnostic Pareto operation; it never selects a placement.

```
python tools/tracehoi/compare_scene_candidates.py build \
  --package /absolute/reviewed_scenes --package-sha256 PACKAGE_SHA \
  --validation /absolute/mask_validation --validation-sha256 VALIDATION_FILES_SHA \
  --case alapuse02v3n60 --purpose candidate_comparison --output /new/output
python tools/tracehoi/check_candidate_comparison.py
```

The two SHA arguments identify `package.json` and validation `files.json`. Verification requires the independently recorded comparison `files.json` SHA. All inputs stay unchanged. The original RGB-only reference annotator remains usable with its original protocol binding.

## Remaining work

A separate reference can quantify mask disagreement when supplied. Metric scale, geometric accuracy, containment and physical contact require separate evidence. No candidate, scale or pipeline placement is approved by this module; `selected_candidate` and `accepted_scale` remain null, and placement flags remain false.

## Retention

After publication and replacement verification, the manual G9 carrier can archive and Trash only the complete F8 working tree. It retains the original terminal, a complete-tree archive, the original source package and the exact F8 validation packet including the annotator. Keep human review/reference JSON, original images and masks, model assets, complete evidence archives and current partial outputs. Do not empty Trash or delete original terminal guards.
