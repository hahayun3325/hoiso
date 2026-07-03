# alapuse01 — Gate D-0 fit v1a3 final decision

## Decision

PARTIAL_PASS_STRUCTURAL_FRAME_FOUND.

## Candidate decision

Reject A, B, C, D as final seeds.

Accept E_aligned_mano_active_raw as the best structural non-GT candidate, but not as a contact-valid seed yet.

## Reason

A/B/D visually touch the wrong laptop region, even though the metric says hand-to-lid is close. This indicates the scorer is being fooled by imperfect part labels.

C shows broken double-laptop geometry and scale/frame mismatch.

E has the best overall hand-laptop spatial relation, but the hand floats above the laptop and does not yet close contact with the lid/screen.

## Next step

Run v1a4 E-candidate contact-closing diagnostic.

The goal is to test whether E can be corrected by a small physically plausible object/lid adjustment without GT.
