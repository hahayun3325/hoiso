# alapuse01 — Gate D-0 per-part oracle v1.1 connected hinge decision

## Decision

Fill after visual inspection.

## What v1.1 tests

V1.1 changes the model from free independent part ICP to a connected articulated laptop model:

- one shared global scale
- keyboard_base as root
- screen rotates around estimated hinge axis
- no independent screen translation
- no independent per-part scale

## Decision rule

PASS if:

- collapse_flag = false
- bbox volume ratio is close to 1
- screen and base are visually connected
- hinge gap is small
- object covers the GT laptop reasonably

PARTIAL PASS if:

- metrics improve but hinge is visually wrong
- object does not collapse but hinge axis is inaccurate

FAIL if:

- object collapses
- screen/base disconnect badly
- metrics are worse than v1

## Next step

If v1.1 is partial pass, implement v1.2 hinge-axis refinement.
If v1.1 passes, rerun Gate C v3 contact verification in the repaired frame.
