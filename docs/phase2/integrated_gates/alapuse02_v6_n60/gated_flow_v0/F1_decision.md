# alapuse02v6n60 gated flow F1 decision

Decision: CONDITIONAL_PASS_F1_GEOMETRY_ONLY

## Implementation checks (all PASS)
- Fixed Gate A object preloaded successfully (15,086 verts).
- Final export confirmed to use the frozen Gate A mesh (6/6 optimization
  steps, matching expected step count).
- No traceback, both guidance_out files present and nonempty.

## Object geometry (PASS)
- 2 connected components; dominant component = 99.99% of vertices
  (14,995/14,998). Second component is a 3-vertex artifact, not a
  meaningful fragment.
- Bbox extents [0.590, 0.419, 0.589] consistent with Gate A's
  screen_lid + keyboard_base structure carried through the h2m
  transform -- no collapse, no support-box fusion, no reversion to
  latent-decoded geometry.

## Hand mesh (PASS, pending direct topology confirmation)
- Bbox extents [0.182, 0.253, 0.353], close to F0's [0.188, 0.235,
  0.350] -- no sign of extreme displacement or the fragmentation
  pattern seen in the earlier standalone Gate D v0.1 failure.

## Interaction / contact (DOES NOT MEET FULL-PASS CRITERIA)
Per-fingertip distance to object, F0 vs F1:
  thumb:   7.81cm -> 18.19cm  (worse)
  index:  11.90cm -> 15.30cm  (worse)
  middle: 11.84cm -> 11.31cm  (~same)
  ring:   11.49cm ->  9.13cm  (better)
  pinky:   9.42cm ->  5.81cm  (better)
  mean:   10.49cm -> 11.95cm  (worse)

Visual inspection confirms hand-lid/screen penetration is present in
F1's result (per direct observation of the triage GLB).

## Interpretation

F1 has no contact-specific supervision: the existing generic
distance_loss term operates over the whole hand and whole object with
no knowledge of Gate B/C's verified screen_lid contact hypothesis.
"Object geometry correctly preserved, contact quality unresolved" is
therefore the expected outcome for this specific ablation step, not a
stalled or failed experiment -- it isolates exactly what Gate B/C
contact conditioning (F2) is meant to add.

## Decision

CONDITIONAL_PASS_F1_GEOMETRY_ONLY:
  Gate A object integration into the actual flow-guided optimizer is
  VALIDATED -- first confirmed case in this investigation where a
  gate-verified object mesh survived the real optimizer end-to-end
  without corruption.
  Contact quality is NOT YET resolved and is not expected to be at
  this stage.

Next: proceed to F2 (add Gate B/C screen_lid-restricted contact
constraint) as originally pre-registered.
