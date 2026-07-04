# alapuse01 — Gate D-0 fit v1b1 final decision

## Decision

HARD_CASE_LOCAL_FIT_FAIL.

## Evidence

v1b1 tested whether a small non-GT residual hand correction could move contact from keyboard/base to lid/screen.

The result failed the local-correction rule:

- best candidate: grid_0518
- best candidate translation norm: about 0.125 m
- raw lid patch snap norm: about 0.130 m
- 4 cm and 8 cm clipped corrections still contact keyboard/base
- 12 cm and full/debug correction start to approach lid/screen, but this is too large to call local physical refinement
- base-contact evidence remains strong

## Interpretation

The pipeline correctly detects that the current seed optimizes toward the wrong semantic contact part.

This is not a good seed for full Gate D optimization.

## Research takeaway

alapuse01 is a useful hard negative case:

- part-aware reconstruction and image masks are available,
- hand/object scale and root-frame issues were diagnosed,
- but local fitting cannot recover correct lid/screen contact without a large residual move.

This supports the gate-based design: do not optimize when the verified contact target is not physically trustworthy.

## Next step

Freeze alapuse01 as a hard case.

Run a cheap preflight on another case, preferably amicuse01 if testing another articulated object, or aket01 if a stable positive/control case is needed.
