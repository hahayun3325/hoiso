# DexYCB/OakInk qualitative curation: progress and manuscript boundary

## Current state

The curated set contains 12 source cases and 24 paired images: 4 DexYCB cases and 8 OakInk cases, with one TRACE-HOI expected visualization and one FollowMyHold expected visualization per case. The set covers object completeness, part ownership, selected-hand identity, contact selectivity, symmetric-part ambiguity, thin geometry, and depth/loop ambiguity.

## Evidence boundary

The current manifest labels every image `proposal_expected_visual_not_measured_output`. These assets are preregistered hypothesis illustrations, not experimental results. They may explain the planned stress tests and expected mechanisms, but they must not support claims that one method empirically outperforms the other.

Promotion to `MEASURED_OUTPUT` requires the method run root, run commit, actual mesh paths, selected-hand owner, render receipt/settings, and an unedited rendering of each mesh.

## Panel policy

- Main experimental paper: use only measured output. Prefer four diverse rows per full-width panel.
- Supplement: keep the complete preregistered protocol and later the complete measured comparison/failure packet.
- Current expected panels: caption them explicitly as preregistered expected-behavior illustrations.
- `DexYCB D009 / ycb_17 / p004c03`: the current images reverse the input hand orientation. Exclude the row from positive main-paper claims. Regenerate it to the locked downward-finger-axis contract if retained as a hypothesis; if a measured run has this error, report it as a limitation without repair.

## Recommended main measured subset

- ARCTIC: laptop, notebook, microwave, scissors.
- DexYCB/OakInk: handled pitcher, eyeglasses, binoculars or controller, OakInk scissors.

## Inspection questions

For every measured row, report: (1) object completeness/articulation, (2) selected hand and contacted part, (3) selected versus noncontacting fingers, and (4) source orientation/wrist approach under at least one revealing secondary view.
