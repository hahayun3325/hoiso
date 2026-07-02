# alapuse01 — Gate C v3.2 semantic contact-part audit decision

## Decision

Gate C v3.2 semantic contact-part audit: SEMANTIC FAIL for the current v0 contact target.

## Evidence

The verified hand patch is closest to:

- screen_all
- screen_component_00_sorted_by_area

with mean distance about 0.00555.

It is much farther from:

- hinge
- screen_component_01_sorted_by_area
- keyboard_base

## Visual interpretation

Although the nearest component is labeled as screen_component_00, visual inspection shows the contact markers are around a base-like / penetration region, not the desired upright screen / outer top-lid contact shown in the input image.

## Diagnosis

The distance computation is correct.

The problem is semantic part labeling:

- screen_component_00 is likely a mislabeled or base-like fragment.
- the current contact target is geometrically close but semantically wrong.
- contact-aware scorer v0 should not be used for sandbox optimization yet.

## Decision boundary

Allowed claim:

- scorer v0 works mechanically.
- the local patch is close to the selected mesh component.

Not allowed claim:

- the current patch is verified screen/top-lid contact.
- the current target is ready for optimization.

## Next step

Create Gate C v3.3 with manually selected true top-lid/screen component.

If the hand patch is far from the true top-lid component, then the current object/hand frame does not support the desired input-image contact.
