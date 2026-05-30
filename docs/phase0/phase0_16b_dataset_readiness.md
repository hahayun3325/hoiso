# Phase 0.16b — Dataset Readiness

## Current status

### OakInk

OakInk download completed successfully.

However, split-path readiness still needs verification because the first split images were not found by the strict checker.

Next step:

- inspect folder structure,
- check if files are archived,
- use flexible split resolver.

### ARCTIC

ARCTIC data is not currently available at the required split paths.

Existing folders appear to be code repositories or empty dataset placeholders.

Next step:

- inspect local ARCTIC download script,
- download cropped images if needed,
- re-run split resolver.

### DexYCB

DexYCB toolkit exists, but actual dataset images were not found.

Next step:

- delay download until OakInk/ARCTIC are verified,
- then download/link DexYCB if needed.

## Rule

A dataset is ready only when split image paths resolve to real files.
