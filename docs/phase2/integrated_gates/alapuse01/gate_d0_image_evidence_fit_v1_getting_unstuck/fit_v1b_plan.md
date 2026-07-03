# alapuse01 — Gate D-0 fit v1b plan

## Goal

Fix the v1 failure where the hand appears underneath the base.

## Diagnosis from v1

The v1 fitter successfully used lid/base masks and depth, but it did not produce a correct hand-lid interaction.

The most likely causes are:

1. hand/object frame mismatch,
2. semantic contact prior not explicitly consumed,
3. contact loss selected nearest 3D hand patch instead of image-derived right-finger-to-lid prior,
4. depth/mask fitting dominated the interaction term.

## v1b change

Before running another optimizer:

1. Choose hand transform using v1a diagnostic.
2. Explicitly load `image_derived_contact_prior_v1.json`.
3. Select contact region from the right hand side / finger-side vertices, not global nearest vertices.
4. Increase contact weight only after the correct hand frame is confirmed.
5. Add base-hand repulsion so the hand is not under/inside base.

## Decision rule

PASS:
  hand and lid are in a plausible interaction frame,
  lid moves toward fingers,
  base does not cover the hand,
  contact mean < 0.040 m at minimum, ideally < 0.015 m.

FAIL:
  hand still under base,
  lid/base collapse,
  contact improves only by penetration.
