# AUTO-V2 spatial proposal prompt

Analyze only the attached `contextual_inpaint.png`. The image coordinates use normalized values from 0.0 to 1.0, with `(0,0)` at the upper-left and `(1,1)` at the lower-right.

The target is an **open small wooden toy laptop**. It has two physical parts: an upright lid/screen and a horizontal keyboard base connected at a hinge. The small house-like wooden object directly below the base is a **support/distractor**, not part of the laptop. The large white horizontal surface is the **tabletop**, also not part of the laptop.

Return tight boxes for these visible regions:

1. `whole_laptop`: lid + base only; exclude support and tabletop.
2. `laptop_lid`: full external wooden lid frame plus dark screen.
3. `laptop_base`: keyboard, touchpad, and full base silhouette only.
4. `wooden_support`: only the small house-like support directly below the laptop.
5. `tabletop`: only the large white table surface.

Do not repair pixels. Do not infer hidden geometry. Do not use Candidate I or any manually reviewed silhouette. If any required region cannot be localized confidently, set `uncertain` to true.

Return raw JSON only, with no code fence and no extra text:

```json
{
  "schema_version": "auto_v2_spatial_proposal_v1",
  "case_id": "alapuse02v3n60",
  "uncertain": false,
  "regions": {
    "whole_laptop": {
      "box_norm_xyxy": [0.0, 0.0, 1.0, 1.0],
      "confidence": 0.0,
      "visible": true,
      "description": ""
    },
    "laptop_lid": {
      "box_norm_xyxy": [0.0, 0.0, 1.0, 1.0],
      "confidence": 0.0,
      "visible": true,
      "description": ""
    },
    "laptop_base": {
      "box_norm_xyxy": [0.0, 0.0, 1.0, 1.0],
      "confidence": 0.0,
      "visible": true,
      "description": ""
    },
    "wooden_support": {
      "box_norm_xyxy": [0.0, 0.0, 1.0, 1.0],
      "confidence": 0.0,
      "visible": true,
      "description": ""
    },
    "tabletop": {
      "box_norm_xyxy": [0.0, 0.0, 1.0, 1.0],
      "confidence": 0.0,
      "visible": true,
      "description": ""
    }
  },
  "relations": {
    "laptop_is_open": true,
    "lid_above_base": true,
    "base_above_support": true,
    "support_above_tabletop": true,
    "support_is_not_part_of_laptop": true,
    "tabletop_is_not_part_of_laptop": true
  },
  "notes": ""
}
```
