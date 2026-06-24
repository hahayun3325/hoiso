# Manual MLLM contact prompt template

You are analyzing one hand-object interaction image for 3D reconstruction.

Goal:
Identify conservative finger-to-object-part contact proposals.

Use the provided object part schema. Return JSON only.

Important rule:
Be conservative. Do not mark contact if the finger is only close but not visibly touching. Prefer `near_contact` or `uncertain` when unsure.

Input fields:
- case_id
- object category
- object part names
- visible image
- optional depth or rendered mesh snapshot
- left/right hand if known

Return format:

{
  "case_id": "",
  "frame_id": "single_image",
  "camera_view": "exocentric | egocentric | uncertain",
  "hands_visible": ["left", "right", "uncertain"],
  "contacts": [
    {
      "hand": "left | right | uncertain",
      "finger": "thumb | index | middle | ring | little | palm | unknown",
      "object_part": "",
      "state": "contact | near_contact | no_contact | uncertain",
      "confidence": 0.0,
      "visual_evidence": "",
      "false_positive_risk": "low | medium | high",
      "should_use_for_optimization": true
    }
  ],
  "global_notes": ""
}

Rules:
1. Only use object_part names from the provided part schema.
2. Contact means physical touch, not visual overlap.
3. Mark false_positive_risk high if the finger is occluded, depth is ambiguous, or the hand is only visually close.
4. Set should_use_for_optimization=true only for confident contact.
5. If no reliable contact exists, return an empty contacts list.
