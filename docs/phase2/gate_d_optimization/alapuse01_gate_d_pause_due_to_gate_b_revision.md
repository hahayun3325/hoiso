# alapuse01 — Gate D pause due to Gate B revision

## Decision

Gate D semantic optimization: PAUSE.

Optimizer-v1/v2 with the old keyboard_base target should be treated as code/mechanics smoke tests only.

## Reason

The previous Gate B contact proposal used:

right index -> keyboard_base

That proposal was inferred from the selector-v41 reconstruction. However, selector-v41 has weak object alignment: the laptop is smaller and shifted relative to GT.

The cropped input and GT/reference evidence suggest the right hand is instead contacting the screen/top-lid panel.

## Consequence

Any Gate D optimizer using the old keyboard_base target cannot be treated as a meaningful physical result.

## Next step

Revise Gate B using cropped input and GT/reference evidence, then rerun Gate C verification.

## Claim boundary

Allowed:
- optimizer-v1/v2 code path works mechanically
- contact/collision losses can be computed
- old keyboard_base target can be kept as a deprecated debugging hypothesis

Not allowed:
- final contact correctness
- physical pass
- laptop alignment improvement
- GT object improvement
