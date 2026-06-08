# Contact-Aware Selector — Next Step

## Current problem

The internal selector chooses the object candidate with better completeness / lower fragmentation.

This helps object integrity, but it can hurt hand-object alignment because the selected object is not chosen based on contact.

## Evidence from OakInk split000

Compared with the baseline, GPT-5.5 + selector improves object completeness but worsens hand-object distance.

This shows the current selector is an object-completeness selector, not a contact-aware selector.

## Next selector score

Future candidate selection should use:

- object completeness
- object silhouette consistency
- MoGe partial point-cloud consistency
- text/shape consistency
- hand-object contact distance
- penetration penalty

A simple score is:

C = w_complete * C_complete
  + w_sil * C_silhouette
  + w_point * C_point
  + w_contact * C_contact
  - w_pen * penetration

## Expected benefit

This should preserve complete object geometry while avoiding candidates that drift away from the hand.
