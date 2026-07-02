# alapuse01 — Gate D-0 v1 image-evidence articulated fitting

## Why this starts now

Gate C v3.3 proved that the correct top-lid/screen component is far from the hand patch.

Therefore the contact target cannot be repaired inside Gate C.

The object state must be repaired upstream.

## Core change

Do not derive contact from nearest-neighbor geometry.

Instead:

1. Use image evidence to define semantic contact:
   right hand/fingers touch the laptop lid outer surface.
2. Pin this contact to the true lid/top-screen part.
3. Optimize object variables so the lid moves toward the hand:
   - shared scale s
   - keyboard/base root pose T_base
   - lid hinge angle theta

## Losses to add

- whole object silhouette loss
- per-part silhouette loss
- depth/disparity loss if available
- image-derived lid contact loss
- hinge connectivity loss
- inter-part penetration loss
- hand-object penetration loss

## What not to do

- do not run Gate D sandbox on the current v0 contact target
- do not continue Gate C nearest-neighbor patch search
- do not trust current PartField labels without image/mask relabeling

## Runtime target

No brute-force grid search.

Target runtime under 10 minutes:

- semantic evidence and masks: cached
- deterministic part relabel: <1 min
- initialization: 1–2 min
- 50–150 Adam steps: 1–2 min
- verification: 1–2 min
