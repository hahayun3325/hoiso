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

## ascis01 shape-sanity check result (final)

watertight = True
euler_number = -332  (expect ~2 for a clean closed genus-0 box)
area^1.5 / volume = 499.05  (high = irregular/ragged surface)

Watertight does not imply clean: euler_number this far from 2 indicates
hundreds of small holes/handles or disconnected sealed fragments stitched
into one mesh, not a coherent box. The high area/volume ratio independently
confirms a fuzzy, high-surface-area shell rather than six flat panels.

Decision: ascis01's numeric fingertip-distance pass was COINCIDENTAL.
The bounding box happened to land at a plausible scale despite fragmented,
untrustworthy underlying geometry. FAIL_FRAGMENTED_GEOMETRY (final).

## Updated pipeline-level finding (final for this round)

Three consecutive non-aket01 cases (abox01, amicuse01, ascis01) have now
failed a genuine shared-frame check, each for a related but distinct
reason (oversized/contaminated object; fragmented disjoint object;
watertight-but-topologically-fragmented object). Only aket01 -- the
simplest, least-occluded, highest-contrast-background case -- has passed.
This is a strong enough pattern to treat guidance_out shared-frame
reliability as input-difficulty-dependent, and to prioritize finding or
constructing an easier input case over further debugging of harder ones.
