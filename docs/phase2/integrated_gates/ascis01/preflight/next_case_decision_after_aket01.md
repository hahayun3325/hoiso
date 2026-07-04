# Next case decision after aket01

## Decision

Use ascis01 as the next active integrated-gates case.

## Why aket01 stops here

aket01 is now frozen as a positive-control pass. It validates shared-frame loading,
contact verification, contact target scoring, and proxy collision push-out.

## Why not abox01 immediately

abox01 is useful as a penetration-repair fallback, but it is another mostly rigid
case. It has lower research value after aket01 because it does not strongly test
part-aware articulated reconstruction.

## Why not amicuse01 immediately

amicuse01 is important later, but Phase 1 already showed severe fragmentation and
poor articulated-object quality. Running Gate C/D on it now risks reproducing the
same failure before we can isolate the value of contact verification.

## Why ascis01

ascis01 is a cleaner middle step:
- articulated / multi-part object,
- simpler than microwave,
- failure mode is floating/contact rather than catastrophic fragmentation,
- useful test of whether Gate A can provide meaningful parts before Gate C/D.

## Decision rule

If ascis01 has usable part assets and a shared frame:
  proceed to Gate C contact verification.

If ascis01 parts are fused/fragmented or frame is broken:
  stop early and switch to abox01 as the penetration-repair showcase.
