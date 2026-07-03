# alapuse01 — Gate D-0 fit v1a4 final decision

## Decision

PARTIAL_DIAGNOSTIC / FAIL_AS_PHYSICAL_REPAIR.

## Evidence

E_original:
- hand floats far above the laptop lid/screen.
- visual scale between hand and laptop looks suspicious.

E_whole_object_snap_to_hand_patch:
- closes visible fingertip/lid contact.
- contact mean drops to about 0.038 m.
- but it requires moving the whole laptop by about 0.298 m.
- this is not a physically meaningful articulated repair.

E_screen_only_snap_debug_not_final:
- closes numeric distance, but breaks the lid-base structure.
- debug upper bound only.

E_best_hinge_rotation_contact_closing:
- hinge-only repair fails.
- best angle is around -5 degrees.
- contact mean remains about 0.305 m.
- no close-contact points are created.

## Interpretation

The problem is likely not just hinge angle.
The current E candidate has a hand/object scale-frame mismatch:
either the hand is too large, the laptop is too small, or the two are not in the same metric frame.

## Next step

Run v1a5 scale-frame audit before any v1b optimization.
