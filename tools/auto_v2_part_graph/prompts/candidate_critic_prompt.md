# AUTO-V2 blind candidate critic prompt

You are evaluating automatically generated pre-Hunyuan object candidates for the case `alapuse02v3n60`.

The attached panel contains one column per candidate. For each candidate:

- Row 1 is the target-mask overlay on the reference image.
- Row 2 is the binary target mask.
- Row 3 is the exact white-background RGB image proposed for Hunyuan.

The target is an **open small wooden toy laptop**. A safe candidate must satisfy all of the following:

1. Preserve the target identity and original open-laptop orientation.
2. Include the complete external lid frame and dark screen.
3. Include the complete keyboard/base silhouette, including visible corners.
4. Preserve the lid-base hinge relationship.
5. Exclude the small house-like wooden support below the laptop.
6. Exclude the large white tabletop.
7. Exclude hands and arms.
8. Avoid invented large geometry or a second object.

Be conservative. If uncertain, mark the candidate unsafe. Do not recommend manual edits. Return raw JSON only, with one review for every candidate ID shown in the panel:

```json
{
  "schema_version": "auto_v2_candidate_critic_v1",
  "case_id": "alapuse02v3n60",
  "uncertain": false,
  "candidate_reviews": [
    {
      "candidate_id": "c01_whole_minus_distractors",
      "target_identity_preserved": false,
      "lid_complete": false,
      "base_complete": false,
      "hinge_preserved": false,
      "support_absent": false,
      "tabletop_absent": false,
      "hand_absent": true,
      "orientation_preserved": true,
      "safe_for_hunyuan": false,
      "confidence": 0.0,
      "failure_reasons": []
    }
  ],
  "notes": ""
}
```
