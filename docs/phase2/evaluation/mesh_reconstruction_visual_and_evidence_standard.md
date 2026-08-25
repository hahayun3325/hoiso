# Mesh Reconstruction Visual and Evidence Standard

This is the authoritative standard for TRACE-HOI and FollowMyHold reconstruction figures across datasets.

## Evidence classes

- `MEASURED_OUTPUT`: a rendering of the recorded mesh produced by the named method. Preserve failures; do not repair geometry, pose, articulation, orientation, or contact.
- `EXPECTED_HYPOTHESIS_ILLUSTRATION`: a generated or edited visualization of a preregistered expected behavior. It may explain a mechanism or planned stress test, but it is not experimental evidence.

Every manifest row and caption must state one evidence class. Do not mix classes within a panel.

## Required appearance

1. Show exactly the manifest-owned hand.
2. Use a rigid, visibly faceted solid-magenta hand with a short flat wrist cap.
3. Never show an arm, forearm, sleeve, skin, or long wrist stump.
4. Use a complete solid-cyan object; retain supported geometry as same-cyan relief.
5. Use a square white canvas and soft neutral grounding shadow.
6. Add no in-image title, caption, legend, logo, watermark, arrow, border, or extra object.

## Source-alignment audit

Verify object identity and articulation, contacted part, selected hand, image side, anatomical hand/finger axis, wrist-entry direction, palm/dorsal view, thumb direction, camera, crop, and scale. Finger axis and wrist-entry direction are independent. Reject an unreported reversal or part/side change.

## Paired comparison

Use the same source, selected-hand owner, camera, crop, scale, lighting, and renderer. For measured output, render each real mesh without forcing agreement. For an expected-hypothesis pair, lock all untested factors; if the object branch is shared, lock the complete object and vary only the preregistered contact/placement factor. Never exaggerate the baseline failure.

## Canonical measured-output prompt

Render the supplied measured meshes without changing geometry, pose, articulation, contact, or camera. Show only the manifest-owned rigid faceted magenta hand with a short wrist cap and no arm. Render the complete measured object in cyan. Use a square white canvas and soft neutral shadow. Add no text, title, border, arrow, texture, extra object, or extra hand.

## Expected-illustration contracts

TRACE-HOI: preserve the source camera, hand orientation, object articulation, finger pose, and intended contact; show the selected wrist-capped magenta hand and complete cyan object.

FollowMyHold hypothesis: edit the paired TRACE-HOI anchor; preserve all untested geometry and change only the preregistered moderate contact/placement error. Label both images `EXPECTED_HYPOTHESIS_ILLUSTRATION`.

## Corrected paired controls

- `D009 p004c03`: closed scissors blades point upward and handles remain below. The hand stays on the blade/shank above the pivot; knuckles are above four curled fingers whose axes point downward; a short wrist cap exits image-right. Reject an upward-pointing hand.
- `O042 p006c08`: lock complete eyeglasses and the image-left temple/hinge grasp; only the middle-finger contact changes.
- `O100 p008c02`: lock complete closed scissors; only the declared index/ring contact assignment changes.

## Acceptance

- Evidence class is explicit.
- One manifest-owned magenta wrist-capped hand; no arm.
- Complete cyan object.
- Source articulation, orientation, part, camera, crop, and scale pass audit.
- Only the intended factor changes in an expected-hypothesis pair.
- A hypothesis illustration is never cited as measured evidence.
