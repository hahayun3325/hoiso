# alapuse02_v3c final freeze decision

## Final decision

alapuse02_v3c is frozen at Gate A + Gate B.

Decision labels:
  Gate A = PASS_PARTFIELD_SCREEN_BASE_SPLIT_PARTIAL
  Gate B = PASS_CONSERVATIVE_IMAGE_CONTACT_PROPOSAL
  Gate C/D = FAIL_SHARED_FRAME_FOR_GATE_C_D
  Ratio correction = FAIL_RATIO_SCALE_CORRECTION_BREAKS_ARTICULATED_STRUCTURE

## What succeeded

Gate A succeeded on a real articulated object.

The clean Hunyuan object-only branch produced a usable laptop mesh, and
PartField N=2 produced two meaningful parts:
  - screen_lid
  - keyboard_base

Gate B also succeeded as an image-based semantic contact proposal:
  the input image supports hand-to-lid/screen contact.

## What failed

The 3D shared hand-object frame is still not trustworthy.

The hand does not reliably contact the screen_lid in 3D.
The ratio-derived object scale correction makes the object larger, but it
does not solve contact and it breaks the articulated laptop structure:
  - screen_lid and keyboard_base begin to penetrate or misalign;
  - the hand still does not produce a valid verified contact;
  - cross-case object/hand ratio from aket01 is not a valid final scale
    target for a laptop.

## Interpretation

This is not a Gate A failure.
This is not a Gate B failure.
This is a shared-frame / object-scale / articulated-structure failure
before Gate C/D.

The correct research claim is:
  Gate A+B can work on an articulated laptop case, but Gate C correctly
  refuses to verify an untrustworthy 3D frame.

## Next step

Move Gate C/D demonstration to abox01.
Keep alapuse02_v3c as the articulated Gate A+B success case.
