# alapuse01 — Gate C v3-lite decision

## Decision

Gate C v3-lite keypoint branch: FAIL.

Gate C v3-lite global hand-screen branch: PARTIAL PASS.

## Evidence

The parsed HaMeR fingertip keypoints are far from the active screen part:

- index_tip -> screen distance ≈ 0.688
- middle_tip -> screen distance ≈ 0.701
- ring_tip -> screen distance ≈ 0.716

However, global hand-to-screen distance is very close:

- min = 0.00136
- p1 = 0.00549
- p5 = 0.01393
- p10 = 0.02122

## Interpretation

The red fingertip markers are likely not in the same coordinate frame as the guidance hand mesh.

The hand mesh itself has vertices very close to the screen, so contact may still be geometrically plausible.

## Active seed

Keep the v0 dry-run active seed.

Do not use the rejected v0.1 optimized object.

## Next step

Run Gate C v3.1 local hand-mesh patch verification.

If the local patch is visually on the correct touching fingers, use that patch for contact-aware scorer v0.
