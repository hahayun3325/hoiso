# alapuse01 — Gate C v3.1 local mesh patch decision

## Decision

Gate C v3.1 local hand-mesh patch verification: PASS.

## Evidence

Gate C v3-lite keypoint verification failed because the parsed HaMeR fingertip keypoints were far from the screen.

However, mesh-level verification found a local hand patch close to the screen:

- global hand-to-screen min = 0.00136
- p1 = 0.00549
- p5 = 0.01393
- p10 = 0.02122
- 6 hand vertices within 5 mm
- 27 hand vertices within 10 mm
- 71 hand vertices within 20 mm
- 128 hand vertices within 30 mm
- nearest 1 percent patch = 20 hand vertices

## Visual observation

The red hand-patch markers and blue screen markers fall on the visible hand-screen contact / penetration region.

## Interpretation

The HaMeR fingertip keypoints are unreliable in this fitted mesh frame, likely due to coordinate-frame mismatch or pre-alignment storage.

The dense hand mesh is reliable enough for local contact verification because it is already in the same frame as the active object parts.

## Active verified contact

Use the nearest local hand-mesh patch to the screen/top-lid as the verified contact target.

## Next step

Build contact-aware scorer v0 using this verified mesh patch.

Do not use the failed HaMeR fingertip keypoints for optimization.
