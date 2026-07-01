# alapuse01 — integrated Gate A-D start decision

## Decision

Start integrated gates, but do not enter full FollowMyHold integration yet.

## Reason

The Gate A audit shows:

- keyboard_base: OK
- hinge: OK
- screen: fragmented / noisy
- residual_uncertain: fragmented / noisy

Therefore, the immediate blocker is part quality, not only object optimization.

## Next sequence

1. Repair Gate A parts using component filtering and image/2D mask evidence.
2. Re-run part coherence audit.
3. Build standalone image-evidence articulated fitting.
4. Integrate the successful fitting variables into FollowMyHold flow.

## Target integrated variables

- shared object scale s
- keyboard_base root pose T_base
- screen hinge angle theta
- verified finger-part contact
- collision / interpenetration penalty

## Do not do yet

- Do not run Gate C v3.
- Do not rerun full FollowMyHold.
- Do not continue v1.x grid oracle.
