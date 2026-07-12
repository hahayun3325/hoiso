# alapuse02v6n60 Gate D final freeze decision

Decision: FAIL_GATE_D_AFTER_BOUNDED_ATTEMPTS. FINAL.

## Full attempt sequence

v0.1: FAIL_HAND_FRAGMENTATION -- independent per-vertex push-out
  destroyed MANO topology, invalid nonwatertight sign check used.

v0.2: FAIL_VISUAL_THROUGH_MESH_RESULT -- mean-distance-only loss with
  no penetration term, hand pulled through screen_lid. Signed-distance
  collision statistics later found INVALID (sign convention bug).

v0.3: FAIL_IMPLAUSIBLE_HAND_UNDER_BASE -- whole-object containment
  penalty with no region constraint, hand relocated to a degenerate
  zero-penetration position. Collision statistics INVALID (same bug).

v0.4: FAIL_CONTACT_REGRESSION -- region-constrained probe with a
  hard-cliff drift penalty; optimizer converged to a result worse than
  the untouched baseline on every metric (drift 20.86cm vs 8cm cap,
  fingertip distance worsened, penetration worsened). 1.5 hour runtime.
  Collision statistics INVALID (same sign bug).

v0.5: FAIL_CENTROID_DRIFT_EXCEEDS_CAP -- two-stage, ArtHOI-informed
  design (correct containment direction, restricted fingers, staged
  fit-then-cleanup). Runtime reduced to 8.2s via bounded optimizer and
  small vertex subsets. Optimizer saturated at overly generous bounds
  (+-28.6deg/+-15cm), producing 24.26cm drift.

v0.6: FAIL_NO_SAFE_UPDATE_FOUND (anti-regression fallback correctly
  triggered) -- same two-stage design with tightened bounds
  (+-15deg/+-4cm) and a working anti-regression safeguard. Optimizer
  AGAIN saturated exactly at the new, tighter bound limits, in the
  identical direction as v0.5. Candidate improved raw fingertip
  distance vs baseline (15.17cm vs 25.93cm mean) but failed the drift
  (10.39cm vs 6cm cap) and containment checks; correctly reverted to
  baseline rather than exporting a still-flawed result.

## Key finding

Across v0.5 and v0.6, the optimizer saturated its bound limits in the
SAME direction on every axis at TWO different bound widths. This rules
out "bounds too generous" as the explanation (already ruled in after
v0.5; now ruled out as the ONLY explanation after v0.6's tighter bounds
showed identical behavior). The consistent directional saturation
indicates the fixed target contact patch (nearest screen_lid vertices
to the hand's original centroid) is not reachable from the hand's
actual starting orientation within any plausible rotation/translation
budget -- a target-selection problem, not an optimizer-tuning problem.
Further bound-tightening iterations would not be expected to resolve
this.

## Process note

A path bug in the v0.6 patch script left GATE_D_DIR unchanged from
v0.5, causing v0.6 to overwrite v0.5's output file at the same path
rather than writing to a distinct v0.6 location. Since v0.6's
anti-regression fallback triggered, the file at that shared path is
the REVERTED baseline hand, not a genuine "v0.6 alignment attempt" --
worth noting for the record, though it does not change the underlying
decision, since v0.6's own printed [COMPARE]/[RESULT] log output
(captured independently of the file) already provides the relevant
numeric evidence.

## Final decision

alapuse02v6n60:
  Gate A: PASS_GATE_A_PARTFIELD_N2_SCREEN_BASE_SPLIT.
  Gate B: PASS_GATE_B_CONSERVATIVE_IMAGE_CONTACT_PROPOSAL.
  Gate C v0.2: PASS_GATE_C_SINGLE_HAND_SCREEN_LID_PART_ASSOCIATION,
    WARNING_GATE_C_CONTACT_REGION_MISMATCH.
  Gate D: FAIL_GATE_D_AFTER_BOUNDED_ATTEMPTS. FINAL. Six attempts,
    two of which (v0.5, v0.6) were methodologically sound
    (ArtHOI-informed, correctly-implemented containment direction,
    working anti-regression safeguard) and still failed for a
    consistent, diagnosed reason (unreachable target patch).

This remains a genuine, useful research result: the gates correctly
identify the correct articulated part (screen_lid) and contact
hypothesis (upper/right hand), and Gate C/D correctly refuse to certify
or export an untrustworthy contact-repair result, rather than silently
accepting one. Reliable contact repair for this case would require
either a better-selected target contact region (not nearest-by-distance
heuristic) or a properly contact-fit starting pose from a joint
optimization -- both real findings for the project's diagnostics
section, not just a dead end.
