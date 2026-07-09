# ascis01 / amicuse01 shared-frame triage results

## amicuse01: FAIL (final)

fingertip_min_cm = 24.29, fingertip_mean_cm = 36.25 -- well above 12.5cm.
Component breakdown shows no dominant single component (largest = 70.9%
of vertices, several ~1-1.7m disjoint fragments). Visual panel confirms:
object reconstruction is fractured into disconnected slab-like pieces,
hand mesh does not touch any fragment.

Decision: FAIL_OVERSIZED_OR_CONTAMINATED_OBJECT (confirmed, matches
script's own decision label). Set aside, consistent with abox01.

## ascis01: PASS_NUMERIC, PENDING_VISUAL_CONFIRMATION

fingertip_min_cm = 8.59, fingertip_mean_cm = 10.90 -- clears 12.5cm
threshold, best result in this investigation. Dominant component =
98.3% of vertices at a plausible 0.269m bbox.

However, the visual panel shows a ragged, non-box-like silhouette
inconsistent with the clean rectangular box in the source photo,
likely from segmentation/reconstruction artifacts around the
scissors occluding the box. Per project discipline (numbers alone
are not sufficient), this is NOT yet promoted to a confirmed pass.

Decision: PENDING shape-sanity check (watertightness, euler number,
area/volume irregularity) before treating ascis01 as the next active
Gate C/D case.

## Pipeline-level finding (unchanged, reinforced this round)

The guidance_out shared-frame export is not uniformly reliable across
cases. aket01 (simple, unoccluded, convex object) succeeded; abox01
(two-hand occlusion) and amicuse01 (heaviest occlusion, per project
notes) both failed with oversized/fragmented object reconstructions;
ascis01 (thin occluding tool over a simple box) numerically passes but
shows visual fragmentation artifacts. This is consistent with occlusion
complexity being a driver of shared-frame reliability, not a single
uniform bug -- worth stating precisely as a pipeline-level finding
rather than either "everything is broken" or "it mostly works."
