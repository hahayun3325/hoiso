# aket01 integrated Gate A/C/D positive-control summary

## Role

aket01 is used as the positive/control case after alapuse01 was frozen as a hard case.

## Result summary

| Stage | Decision | Meaning |
|---|---|---|
| Dry-run v0 | DRYRUN_FRAME_MISMATCH | mixed coordinate families failed |
| Dry-run v1 | PASS_SHARED_FRAME | guidance_out hand and object are in the same frame |
| Gate C v0 | PASS_BODY_CONTACT | hand contacts bottle body, not cap/residual |
| Gate D scorer v0 | PASS_CONTACT_TARGET_READY_FOR_SANDBOX | verified contact patch is usable |
| Sandbox v0.1 | PASS_STABLE_NO_MOVE_BEST | unsigned contact proxy stable |
| Sandbox v0.2 | FAIL_SIGNED_COLLISION_DEEP_INTERSECTION_AS_IMPLEMENTED | unsigned proxy hides collision |
| Sandbox v0.2a | SDF_UNRELIABLE_BODY_NOT_WATERTIGHT | raw SDF cannot be trusted as final |
| Sandbox v0.3 | PASS_PROXY_PUSHOUT_REDUCES_COLLISION_KEEP_CONTACT | robust proxy push-out reduces collision while preserving contact |

## Main takeaway

aket01 proves that the integrated gates can work end-to-end:

1. load a correct shared frame,
2. verify the correct object part contact,
3. build a contact target,
4. detect that contact-only is not enough,
5. use a collision-aware proxy to reduce penetration without destroying contact.

## Limitation

This is not a final physical collision-free reconstruction because the body mesh is fragmented and not watertight.

## Next case

Move to abox01 to test a stronger penetration-repair case.
