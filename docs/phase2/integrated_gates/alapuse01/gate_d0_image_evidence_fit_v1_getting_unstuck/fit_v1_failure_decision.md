# alapuse01 — Gate D-0 fit v1 failure decision

## Decision

Gate D-0 image-evidence articulated fitting v1: FAIL.

## What worked

- The missing articulated fitter script was created.
- The script ran successfully.
- `fit_v1_scene.glb` was generated.
- Loss decreased during optimization.
- Commit and push succeeded.

## Numeric result

Final contact patch to lid distance:

- min = 0.0227 m
- mean = 0.0549 m
- max = 0.0919 m

According to the current decision rule, this is a fail because mean contact distance is larger than 0.040 m.

## Visual result

The hand appears underneath / behind the laptop base rather than touching the lid/screen as shown in the input image.

## Diagnosis

The v1 fitter used image masks/depth for lid and base, but the contact term did not explicitly consume the Gate B semantic prior.

The contact patch was selected by nearest 3D hand vertices to the initial lid, so it can be wrong if the hand and object are not in the same frame.

Likely causes:

1. hand/object frame mismatch,
2. semantic contact prior not explicitly used,
3. depth/mask losses dominate over contact,
4. hinge/object fitting moves the object while hand remains fixed.

## Decision boundary

Allowed claim:

- v1 is a runnable diagnostic fitter.
- v1 shows that mask/depth fitting alone does not fix HOI contact.

Not allowed claim:

- v1 repairs the laptop pose.
- v1 is ready for Gate C or sandbox contact optimization.

## Next step

Run Gate D-0 fit v1a hand-frame and contact-prior diagnostic.

Do not proceed to Gate C or sandbox optimization yet.
