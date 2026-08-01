# Gate-C semantic hand-identity review prompt

You are given:

1. the original target RGB crop;
2. a contact sheet of deterministic projected hand candidates;
3. labels showing each candidate ID and deterministic route.

Task: identify whether any candidate corresponds to the **upper physical hand touching the laptop lid/screen** in the target image.

Rules:

- Judge physical hand identity, upper/lower role, handedness, and rough finger articulation.
- Do not estimate a 3D transform.
- Do not choose a candidate whose label says `HOLD_CANDIDATE_INVALID`, `HOLD_REFLECTED_ONLY`, or whose identity is not source verified.
- If evidence is ambiguous, return `hold`.
- Return exactly one JSON object and no prose.

```json
{
  "decision": "select or hold",
  "selected_candidate_id": "candidate ID or null",
  "physical_hand": "upper",
  "handedness": "left, right, or uncertain",
  "confidence": 0.0,
  "reasons": [
    "brief visual reason 1",
    "brief visual reason 2"
  ]
}
```
