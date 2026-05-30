# Optional Object Fallback Switch Plan

## Goal

Keep the original FollowMyHold output unchanged by default, while allowing fallback correction for ablation studies.

## Proposed switches

Default mode:

FOHO_ENABLE_OBJECT_FALLBACK=0
FOHO_FALLBACK_ALIGN_MODE=none

Fallback bbox mode:

FOHO_ENABLE_OBJECT_FALLBACK=1FOHO_FALLBACK_ALIGN_MODE=bbox

## Modes

- `none`: use original final object
- `select_only`: select trusted object source but do not align
- `bbox`: select trusted object source and bbox-align to final object frame
- `se3_contact`: future contact-aware SE(3) refinement

## Why this matters

This allows clean comparisons:

1. original FollowMyHold output,
2. prompt-improved output,
3. fallback-enabled output,
4. future contact-refined output.  
