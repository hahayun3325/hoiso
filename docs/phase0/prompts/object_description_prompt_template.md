# Object Description Prompt Template

## Goal

Generate an object description for HOI reconstruction, not a generic caption.

## Prompt

Describe the held object for 3D reconstruction.

Return one concise sentence with these fields:

1. category
2. brand/text if visible
3. overall 3D shape
4. flat/round surfaces
5. visible silhouette
6. edges/corners
7. material/color if useful
8. negative shape constraint: what it is not

Do not describe the person or hand.
Focus only on the object geometry.

## Example output

A rectangular SPAM canned meat tin with flat front and back faces, rounded rectangular corners, a flat metal top, and a boxy non-cylindrical body; it is not a round soda can or soup can.

## JSON version

{
  "object_category": "",
  "visible_text_or_brand": "",
  "overall_shape": "",
  "flat_or_round_surfaces": "",
  "silhouette": "",
  "edges_or_corners": "",
  "material_or_color": "",
  "negative_shape_constraint": "",
  "reconstruction_prompt": ""
}
