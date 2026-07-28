#!/usr/bin/env python3
"""Validate an exact-schema VLM spatial proposal and render its boxes.

Usage:
  python3 validate_spatial_proposal.py RAW_RESPONSE.json IMAGE.png OUTPUT_DIR

This utility deliberately avoids argparse/SystemExit(2). It prints PASS/HOLD markers
and writes no validated artifact when the response contract is invalid.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sys
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    if len(sys.argv) != 4:
        print("[HOLD] SPATIAL_PROPOSAL_USAGE=RAW_RESPONSE.json IMAGE.png OUTPUT_DIR")
        return

    response_path = Path(sys.argv[1])
    image_path = Path(sys.argv[2])
    out_dir = Path(sys.argv[3])

    if not response_path.is_file() or not image_path.is_file():
        print(
            "[HOLD] SPATIAL_PROPOSAL_INPUT_MISSING="
            f"response={response_path.is_file()} image={image_path.is_file()}"
        )
        return

    try:
        from PIL import Image, ImageDraw
    except Exception as error:  # pragma: no cover - environment dependent
        print(f"[HOLD] PIL_IMPORT_FAILED={type(error).__name__}: {error}")
        return

    try:
        raw_text = response_path.read_text(encoding="utf-8").strip()
        # Exact raw JSON only. Code fences or explanatory text are a contract failure.
        data = json.loads(raw_text)
    except Exception as error:
        print(f"[HOLD] SPATIAL_PROPOSAL_JSON_INVALID={type(error).__name__}: {error}")
        return

    required_top = {
        "schema_version",
        "case_id",
        "uncertain",
        "regions",
        "relations",
        "notes",
    }
    missing_top = sorted(required_top - set(data.keys()))
    if missing_top:
        print("[HOLD] SPATIAL_PROPOSAL_TOP_KEYS_MISSING=" + ",".join(missing_top))
        return

    if data.get("schema_version") != "auto_v2_spatial_proposal_v1":
        print(f"[HOLD] SPATIAL_PROPOSAL_SCHEMA={data.get('schema_version')}")
        return
    if data.get("case_id") != "alapuse02v3n60":
        print(f"[HOLD] SPATIAL_PROPOSAL_CASE_ID={data.get('case_id')}")
        return
    if data.get("uncertain") is not False:
        print("[HOLD] SPATIAL_PROPOSAL_UNCERTAIN=true")
        return

    expected_labels = (
        "whole_laptop",
        "laptop_lid",
        "laptop_base",
        "wooden_support",
        "tabletop",
    )
    regions = data.get("regions")
    if not isinstance(regions, dict):
        print("[HOLD] SPATIAL_PROPOSAL_REGIONS_NOT_OBJECT")
        return

    missing_regions = [label for label in expected_labels if label not in regions]
    if missing_regions:
        print("[HOLD] SPATIAL_PROPOSAL_REGIONS_MISSING=" + ",".join(missing_regions))
        return

    relations = data.get("relations")
    expected_relations = {
        "laptop_is_open": True,
        "lid_above_base": True,
        "base_above_support": True,
        "support_above_tabletop": True,
        "support_is_not_part_of_laptop": True,
        "tabletop_is_not_part_of_laptop": True,
    }
    if not isinstance(relations, dict):
        print("[HOLD] SPATIAL_PROPOSAL_RELATIONS_NOT_OBJECT")
        return
    failed_relations = [
        key for key, expected in expected_relations.items()
        if relations.get(key) is not expected
    ]
    if failed_relations:
        print("[HOLD] SPATIAL_PROPOSAL_RELATIONS_FAILED=" + ",".join(failed_relations))
        return

    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    validated: dict[str, Any] = {
        "schema_version": "auto_v2_spatial_boxes_px_v1",
        "case_id": "alapuse02v3n60",
        "source_image": str(image_path),
        "source_image_sha256": sha256(image_path),
        "image_size_wh": [width, height],
        "regions": {},
        "relations": relations,
    }

    errors: list[str] = []
    for label in expected_labels:
        item = regions[label]
        if not isinstance(item, dict):
            errors.append(f"{label}:not_object")
            continue
        box = item.get("box_norm_xyxy")
        confidence = as_float(item.get("confidence"))
        visible = item.get("visible")
        if not isinstance(box, list) or len(box) != 4:
            errors.append(f"{label}:box")
            continue
        coords = [as_float(v) for v in box]
        if any(v is None for v in coords):
            errors.append(f"{label}:box_non_numeric")
            continue
        x0, y0, x1, y1 = [float(v) for v in coords if v is not None]
        if not (0.0 <= x0 < x1 <= 1.0 and 0.0 <= y0 < y1 <= 1.0):
            errors.append(f"{label}:box_range")
            continue
        if confidence is None or not (0.0 <= confidence <= 1.0):
            errors.append(f"{label}:confidence")
            continue
        if visible is not True:
            errors.append(f"{label}:not_visible")
            continue

        px = [
            max(0, min(width - 1, round(x0 * width))),
            max(0, min(height - 1, round(y0 * height))),
            max(1, min(width, round(x1 * width))),
            max(1, min(height, round(y1 * height))),
        ]
        if px[2] <= px[0] or px[3] <= px[1]:
            errors.append(f"{label}:pixel_box_invalid")
            continue
        validated["regions"][label] = {
            "box_norm_xyxy": [x0, y0, x1, y1],
            "box_px_xyxy": px,
            "confidence": confidence,
            "visible": True,
            "description": str(item.get("description", "")),
        }

    if errors:
        print("[HOLD] SPATIAL_PROPOSAL_VALIDATION=" + ",".join(errors))
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    boxes_path = out_dir / "boxes_px.json"
    overlay_path = out_dir / "boxes_overlay.png"
    report_path = out_dir / "validation_report.json"
    if any(path.exists() for path in (boxes_path, overlay_path, report_path)):
        print(f"[HOLD] SPATIAL_PROPOSAL_OUTPUT_EXISTS={out_dir}")
        return

    palette = {
        "whole_laptop": (255, 255, 0),
        "laptop_lid": (0, 255, 0),
        "laptop_base": (0, 160, 255),
        "wooden_support": (255, 0, 0),
        "tabletop": (255, 0, 255),
    }
    draw_image = image.copy()
    draw = ImageDraw.Draw(draw_image)
    for label in expected_labels:
        x0, y0, x1, y1 = validated["regions"][label]["box_px_xyxy"]
        color = palette[label]
        draw.rectangle((x0, y0, x1, y1), outline=color, width=4)
        draw.rectangle((x0, max(0, y0 - 20), min(width, x0 + 180), y0), fill=(0, 0, 0))
        draw.text((x0 + 3, max(0, y0 - 18)), label, fill=color)

    boxes_path.write_text(json.dumps(validated, indent=2) + "\n", encoding="utf-8")
    draw_image.save(overlay_path)
    report = {
        "status": "pass",
        "response_path": str(response_path),
        "response_sha256": sha256(response_path),
        "boxes_path": str(boxes_path),
        "overlay_path": str(overlay_path),
        "region_count": len(expected_labels),
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"[PASS] SPATIAL_PROPOSAL_VALIDATED={boxes_path}")
    print(f"[PASS] SPATIAL_PROPOSAL_OVERLAY={overlay_path}")


if __name__ == "__main__":
    main()
