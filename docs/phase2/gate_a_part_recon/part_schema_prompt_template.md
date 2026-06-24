# Part schema prompt template for Gate A

Describe the held object for part-aware 3D reconstruction.

Return one JSON object only. Do not include markdown.

Required fields:

{
  "case_id": "",
  "object_category": "",
  "rigid_or_articulated": "rigid | articulated | uncertain",
  "main_parts": [
    {
      "part_name": "",
      "part_role": "",
      "expected_geometry": "",
      "contact_relevance": "",
      "thin_or_small": true,
      "visible_in_image": "yes | partial | no | uncertain"
    }
  ],
  "joint_graph": [
    {
      "parent_part": "",
      "child_part": "",
      "joint_type": "fixed | hinge | pivot | sliding | unknown",
      "joint_location_hint": "",
      "open_closed_state": ""
    }
  ],
  "part_segmentation_guidance": {
    "merge_parts_if": "",
    "split_parts_if": "",
    "do_not_create_parts_for": ""
  },
  "negative_constraints": [
    ""
  ],
  "confidence_notes": ""
}

Rules:
1. Focus only on object parts, not the person.
2. Prefer 2–6 meaningful parts, not many tiny fragments.
3. For rigid objects, use fixed joints or an empty joint graph.
4. For articulated objects, name the hinge/pivot and open/closed state if visible.
5. Mention thin structures explicitly, such as blades, handles, caps, doors, screens, or hinges.
6. Be conservative: if the part is not visible, mark it as partial or uncertain.
