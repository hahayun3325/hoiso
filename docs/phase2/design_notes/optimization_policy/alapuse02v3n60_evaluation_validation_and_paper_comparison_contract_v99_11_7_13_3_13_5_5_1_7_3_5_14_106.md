# Evaluation and validation contract for alapuse02v3n60

Status: protocol contract. Published values are references; forecast ranges
are hypotheses and must not be reported as measured results.

## Separation of responsibilities

F0 is deterministic and non-optimizing. It validates checkpoint lineage,
hashes, serialized schemas, finite values, attempt/rollback semantics,
terminal export, zero-update replay, and panel immutability.

Human review is the final semantic ACCEPT or REJECT for the case. D1 is not
used as a terminal VLM jury.

Paper comparison is a separate dataset evaluation. Internal losses are not
benchmark metrics. In particular, loss_collision is neither ArtHOI Co2 nor
Follow My Hold intersection volume.

## Terminal ownership

| State | Canonical checkpoint owner | Field |
|---|---|---|
| Global hand rotation/translation | accepted H0 | parameters.global_hand_rotation, parameters.global_hand_translation |
| MANO articulation | accepted H1 | selected_so3_residual |
| Global object rotation/translation | accepted O0 | parameters.global_object_rotation, parameters.global_object_translation |
| Final joint state | accepted J0 | four global R/t tensors plus unchanged H1 residual |

H1 may carry accepted_H0_rotation and accepted_H0_translation as lineage
copies. Live-binder names are not assumed to be serialized checkpoint keys.

## Follow My Hold comparison

Use the exact 1,000-image lists for OakInk, Arctic, and DexYCB. Compute CD,
F5, F10, and intersection volume only on successful reconstructions and
reconstruction rate over the full list. Match surface sampling, units,
alignment, mesh repair, evaluator, and aggregation.

| Dataset, published Ours | F5 up | F10 up | CD cm2 down | I.V. cm3 down | R.R. up |
|---|---:|---:|---:|---:|---:|
| OakInk | 0.179 | 0.322 | 1.80 | 5.96 | 0.87 |
| Arctic | 0.160 | 0.288 | 2.57 | 5.08 | 0.92 |
| DexYCB | 0.158 | 0.300 | 2.04 | 7.02 | 0.58 |

Provisional single-case planning ranges, not results: CD 2--6 cm2, F5
0.10--0.25, F10 0.22--0.45, and I.V. 4--12 cm3. Reconstruction rate is not
estimable from one case.

## ArtHOI comparison

ArtHOI is a monocular-video articulated-object benchmark. A direct claim
requires a temporal/video extension plus the same ground truth, symmetry,
contact annotations, evaluator, and aggregation.

| ArtHOI-RGBD object, published Ours | CD mm down | MSSD mm down | F10 percent up | F5 percent up |
|---|---:|---:|---:|---:|
| Headphone | 8.124 | 30.43 | 69.68 | 42.19 |
| Scissor | 4.256 | 15.14 | 92.57 | 65.00 |
| Candy Box | 4.104 | 17.67 | 92.55 | 71.63 |
| CD Drive | 3.334 | 9.71 | 96.01 | 78.75 |
| Stapler | 4.487 | 20.15 | 91.63 | 67.94 |
| Unweighted mean of displayed rows | 4.861 | 18.62 | 88.488 | 65.102 |

Published Co2 with MLLM: 0.029 ArtHOI-RGBD, 0.022 RSRD, and 0.039
ArtHOI-Wild. Published ASR IoU/SR: 0.905/100%, 0.876/100%, and 0.882/100%.
Co2 measures hand-object collision/contact alignment, not object pose alone.

Provisional planning ranges, not results: CD 10--40 mm, MSSD 25--100 mm,
F10 25--70%, F5 10--45%, and silhouette IoU 0.75--0.90. Co2 and video
success rate are not estimable for the current single-frame case.

## Current measured internal evidence

J0 completed five attempts and five accepted updates with no rollback.
From accepted upstream state to terminal J0: hand rotation 0.079129 degrees,
hand translation 0.725155 mm, object rotation 0.068528 degrees, object
translation 0.497364 mm, H1 residual L2 change 0.0, and total-loss change
-2.029297.

These are engineering diagnostics, not paper-comparable scores.

## Reporting boundary

Every benchmark row must record dataset/list hash, successful and total case
counts, evaluator revision, units, aggregation, and dispersion. Missing
ground-truth metrics remain null, never zero. The case is technically complete
after terminal export, read-only panel PASS, F0 PASS, and human visual ACCEPT.
It is paper-comparable only after the matching benchmark protocol is executed.
