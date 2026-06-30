# alapuse01 — Gate D-0 per-part oracle v1.1 connected hinge

## Goal

Test whether the laptop can be repaired with a physically constrained articulated model.

## Difference from v1

V1 allowed screen, keyboard_base, and hinge to move independently.

V1.1 should enforce:

- one shared global scale
- keyboard_base as root part
- screen moves by rotation around hinge
- no independent screen translation
- no independent per-part scale
- hinge connection must stay close

## Expected decision

If v1.1 aligns the laptop without collapse and without disconnected parts, the articulated model class is confirmed.

If v1.1 still fails, inspect Gate A part quality and hinge-axis estimation.
