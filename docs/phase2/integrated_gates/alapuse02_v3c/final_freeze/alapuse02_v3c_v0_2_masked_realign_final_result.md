# alapuse02_v3c v0.2 object-only-masked MoGe realignment: final result

Decision: FAIL_FREEZE_AT_GATE_A_PLUS_B_MOVE_TO_ABOX01

## What was tried

Per the pre-registered decision branch (MoGe target contamination confirmed
in the frame/scale audit), re-solved the object-only h2m similarity
transform against an object-only-masked MoGe target (mask-indexed
points.exr/npy, eroded, outlier-filtered), jointly re-fitting (s, R, t)
via trimmed ICP + Umeyama, applying ONE resulting transform to both
screen_lid and keyboard_base as a single rigid assembly (preserving the
hinge seam, unlike the earlier ratio-scale attempt).

## Result

Coarse bbox-based initialization succeeded: scale=0.2511 at init, close
to the old (contaminated) transform's scale=0.2237, confirming real
spatial overlap at iteration 0.

However, the ICP loop itself did not converge to a stable fit. Both
inlier_mean and scale decreased monotonically across all 20 iterations
(scale: 0.2033 -> 0.0819), never stabilizing. This is the signature of
ICP scale collapse: with unconstrained similarity-transform fitting and
simple percentile-based trimming (keep = dist < 80th percentile), the
optimizer can minimize point-to-point distance by shrinking the source
cloud onto a small, dense subset of target points, rather than fitting
the true object shape. This is a degenerate optimum, not a real solution.

Final fingertip-to-part distances confirm the collapse produced a
nonsensical result, not a near-miss:
  screen_lid:     min=398.67cm, mean=406.82cm
  keyboard_base:  min=404.06cm, mean=412.02cm

These are off by an order of magnitude relative to the scene's own
~2m bounding box -- not a borderline case near the 12.5cm threshold.

## Root cause summary across all repair attempts on this case

  1. Original guidance.run object branch: corrupted by guided-diffusion
     resampling (established early in this investigation).
  2. Object-only h2m bypass (reusing trustworthy hand): produced a
     uniformly-scaled but undersized object, traced to whole-crop MoGe
     target contamination (~4-6% hand-region points).
  3. Ratio-derived scale correction (aket01 baseline): broke articulated
     structure (per-part centroid scaling) AND the aket01 baseline itself
     was later found to be contaminated by likely support/table geometry.
  4. Translation-only rescue probe: produced single-fingertip "contact"
     without addressing the underlying scale/frame defect; not
     representative of genuine multi-finger grasp.
  5. Object-only-masked MoGe realignment (this attempt): correct init,
     but ICP scale-collapse produced a ~4m-off degenerate result.

Five independently-motivated repair attempts, each targeting a different
plausible root cause, have all failed to produce a trustworthy shared 3D
frame for this case.

## Pipeline lesson (for diagnostics writeup / future reuse)

Unconstrained-scale trimmed ICP with naive percentile-based inlier
selection is prone to scale collapse when source and target point clouds
have ambiguous or partial correspondence structure (e.g. thin/flat
articulated objects, sparse masked targets). A future fix would require
either a scale-regularization term, a correspondence-quality check
independent of raw distance percentile, or a hard bound preventing scale
drift beyond a plausible range around the coarse initialization -- worth
documenting as a known failure mode rather than re-attempting ad hoc.

## Final decision

alapuse02_v3c is frozen at Gate A + Gate B (unchanged from the prior
freeze decision; this attempt does not reopen or change that status,
it closes out the last pre-registered repair branch).

  Gate A = PASS_PARTFIELD_SCREEN_BASE_SPLIT_PARTIAL
  Gate B = PASS_CONSERVATIVE_IMAGE_CONTACT_PROPOSAL
  Gate C/D = FAIL_SHARED_FRAME_FOR_GATE_C_D (final; no further repair
    attempts planned for this case)

Gate C/D demonstration moves to abox01.
