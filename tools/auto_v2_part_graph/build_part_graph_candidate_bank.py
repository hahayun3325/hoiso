#!/usr/bin/env python3
"""Build a bounded automatic candidate bank from part/distractor masks.

Usage:
  python3 build_part_graph_candidate_bank.py BUILD_CONFIG.json

The script creates up to four immutable candidates:
  c01_whole_minus_distractors
  c02_part_union_raw
  c03_part_union_minus_distractors
  c04_part_graph_complete

It never uses Candidate I pixels or coordinates. It avoids argparse/SystemExit(2).
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import sys
from typing import Any


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if len(sys.argv) != 2:
        print("[HOLD] CANDIDATE_BANK_USAGE=BUILD_CONFIG.json")
        return

    config_path = Path(sys.argv[1])
    if not config_path.is_file():
        print(f"[HOLD] CANDIDATE_BANK_CONFIG_MISSING={config_path}")
        return

    try:
        import cv2
        import numpy as np
        from PIL import Image, ImageDraw
    except Exception as error:
        print(f"[HOLD] CANDIDATE_BANK_IMPORT_FAILED={type(error).__name__}: {error}")
        return

    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        case_id = str(cfg.get("case_id", ""))
        if case_id != "alapuse02v3n60":
            print(f"[HOLD] CANDIDATE_BANK_CASE_ID={case_id}")
            return

        context_path = Path(cfg["context_rgb"])
        reference_path = Path(cfg.get("reference_rgb", cfg["context_rgb"]))
        out_root = Path(cfg["output_root"])
        mask_cfg = cfg["masks"]
        thresholds = cfg.get("thresholds", {})

        required_mask_keys = ("lid", "base", "support", "tabletop")
        missing_keys = [key for key in required_mask_keys if key not in mask_cfg]
        if missing_keys:
            print("[HOLD] CANDIDATE_BANK_MASK_KEYS_MISSING=" + ",".join(missing_keys))
            return

        all_paths = [context_path, reference_path] + [Path(mask_cfg[key]) for key in required_mask_keys]
        if "whole" in mask_cfg and mask_cfg["whole"]:
            all_paths.append(Path(mask_cfg["whole"]))
        missing_files = [str(path) for path in all_paths if not path.is_file()]
        if missing_files:
            print("[HOLD] CANDIDATE_BANK_INPUT_MISSING=" + ",".join(missing_files))
            return
        if out_root.exists() and any(out_root.iterdir()):
            print(f"[HOLD] CANDIDATE_BANK_OUTPUT_NOT_EMPTY={out_root}")
            return
        out_root.mkdir(parents=True, exist_ok=True)

        context_image = Image.open(context_path).convert("RGB")
        reference_image = Image.open(reference_path).convert("RGB")
        context = np.asarray(context_image, dtype=np.uint8)
        reference = np.asarray(reference_image.resize(context_image.size), dtype=np.uint8)
        height, width = context.shape[:2]

        def load_mask(path: Path) -> np.ndarray:
            image = Image.open(path).convert("L").resize(context_image.size, Image.Resampling.NEAREST)
            return np.asarray(image, dtype=np.uint8) >= 128

        def fill_holes(mask: np.ndarray) -> np.ndarray:
            u8 = (mask.astype(np.uint8) * 255)
            padded = cv2.copyMakeBorder(u8, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
            flood = padded.copy()
            ffmask = np.zeros((padded.shape[0] + 2, padded.shape[1] + 2), np.uint8)
            cv2.floodFill(flood, ffmask, (0, 0), 255)
            inv = cv2.bitwise_not(flood)
            filled = cv2.bitwise_or(padded, inv)[1:-1, 1:-1]
            return filled >= 128

        def remove_small(mask: np.ndarray, min_pixels: int) -> np.ndarray:
            count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
            out = np.zeros_like(mask)
            for index in range(1, count):
                if int(stats[index, cv2.CC_STAT_AREA]) >= min_pixels:
                    out |= labels == index
            return out

        def clean(mask: np.ndarray, min_pixels: int) -> np.ndarray:
            kernel = np.ones((3, 3), np.uint8)
            u8 = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel, iterations=1)
            u8 = cv2.morphologyEx(u8, cv2.MORPH_OPEN, kernel, iterations=1)
            return remove_small(fill_holes(u8 > 0), min_pixels)

        def dilate(mask: np.ndarray, pixels: int) -> np.ndarray:
            if pixels <= 0:
                return mask.copy()
            size = pixels * 2 + 1
            kernel = np.ones((size, size), np.uint8)
            return cv2.dilate(mask.astype(np.uint8), kernel, iterations=1) > 0

        def centroid(mask: np.ndarray) -> tuple[float, float] | None:
            ys, xs = np.nonzero(mask)
            if len(xs) == 0:
                return None
            return float(xs.mean()), float(ys.mean())

        def component_stats(mask: np.ndarray) -> tuple[int, float]:
            count, _, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
            areas = [int(stats[index, cv2.CC_STAT_AREA]) for index in range(1, count)]
            if not areas:
                return 0, 0.0
            return len(areas), max(areas) / max(1, sum(areas))

        def constrained_hull(
            mask: np.ndarray,
            forbidden: np.ndarray,
            max_gain: float,
            max_forbidden_overlap: float,
        ) -> tuple[np.ndarray, dict[str, Any]]:
            contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return mask.copy(), {"used": False, "reason": "no_contour"}
            contour = max(contours, key=cv2.contourArea)
            raw_area = int(mask.sum())
            if raw_area <= 0:
                return mask.copy(), {"used": False, "reason": "empty"}
            hull = cv2.convexHull(contour)
            proposed = np.zeros_like(mask, dtype=np.uint8)
            cv2.fillConvexPoly(proposed, hull, 1)
            proposed_bool = proposed > 0
            gain = int(proposed_bool.sum()) / max(1, raw_area)
            forbidden_overlap = int((proposed_bool & forbidden).sum()) / max(1, int(proposed_bool.sum()))
            if gain > max_gain:
                return mask.copy(), {"used": False, "reason": "area_gain", "area_gain": gain}
            if forbidden_overlap > max_forbidden_overlap:
                return mask.copy(), {
                    "used": False,
                    "reason": "forbidden_overlap",
                    "area_gain": gain,
                    "forbidden_overlap": forbidden_overlap,
                }
            return proposed_bool, {
                "used": True,
                "reason": "accepted",
                "area_gain": gain,
                "forbidden_overlap": forbidden_overlap,
            }

        min_pixels = int(thresholds.get("min_component_pixels", max(64, int(width * height * 0.0005))))
        distractor_dilate_px = int(thresholds.get("distractor_dilate_px", 1))
        hinge_dilation_px = int(thresholds.get("hinge_dilation_px", max(4, round(min(width, height) * 0.012))))
        max_completion_gain = float(thresholds.get("max_completion_area_gain", 1.35))
        max_distractor_overlap = float(thresholds.get("max_distractor_overlap_fraction", 0.005))
        max_border_touch = float(thresholds.get("max_bottom_border_touch_fraction", 0.02))
        max_components = int(thresholds.get("max_components", 3))
        min_lid_retention = float(thresholds.get("min_lid_retention", 0.90))
        min_base_retention = float(thresholds.get("min_base_retention", 0.90))

        lid = clean(load_mask(Path(mask_cfg["lid"])), min_pixels)
        base = clean(load_mask(Path(mask_cfg["base"])), min_pixels)
        support = clean(load_mask(Path(mask_cfg["support"])), min_pixels)
        tabletop = clean(load_mask(Path(mask_cfg["tabletop"])), min_pixels)
        whole = None
        if mask_cfg.get("whole"):
            whole = clean(load_mask(Path(mask_cfg["whole"])), min_pixels)

        forbidden = dilate(support | tabletop, distractor_dilate_px)
        lid_minus = lid & ~forbidden
        base_minus = base & ~forbidden
        lid_complete, lid_completion = constrained_hull(
            lid_minus, forbidden, max_completion_gain, max_distractor_overlap
        )
        base_complete, base_completion = constrained_hull(
            base_minus, forbidden, max_completion_gain, max_distractor_overlap
        )

        candidate_masks: list[tuple[str, np.ndarray, str]] = []
        if whole is not None:
            candidate_masks.append((
                "c01_whole_minus_distractors",
                clean(whole & ~forbidden, min_pixels),
                "whole_laptop_mask minus support/tabletop masks",
            ))
        candidate_masks.extend([
            (
                "c02_part_union_raw",
                clean(lid | base, min_pixels),
                "raw union of independently box-prompted lid and base masks",
            ),
            (
                "c03_part_union_minus_distractors",
                clean((lid | base) & ~forbidden, min_pixels),
                "part union after deterministic support/tabletop subtraction",
            ),
            (
                "c04_part_graph_complete",
                clean((lid_complete | base_complete) & ~forbidden, min_pixels),
                "constrained convex completion of lid/base after distractor subtraction",
            ),
        ])

        summary: dict[str, Any] = {
            "schema_version": "auto_v2_candidate_bank_v1",
            "case_id": case_id,
            "construction_policy": "fixed_part_graph_candidate_bank",
            "source_context": str(context_path),
            "source_context_sha256": digest(context_path),
            "source_reference": str(reference_path),
            "source_reference_sha256": digest(reference_path),
            "source_masks": {
                key: {"path": str(Path(value)), "sha256": digest(Path(value))}
                for key, value in mask_cfg.items() if value
            },
            "thresholds": {
                "min_component_pixels": min_pixels,
                "distractor_dilate_px": distractor_dilate_px,
                "hinge_dilation_px": hinge_dilation_px,
                "max_completion_area_gain": max_completion_gain,
                "max_distractor_overlap_fraction": max_distractor_overlap,
                "max_bottom_border_touch_fraction": max_border_touch,
                "max_components": max_components,
                "min_lid_retention": min_lid_retention,
                "min_base_retention": min_base_retention,
            },
            "completion": {
                "lid": lid_completion,
                "base": base_completion,
            },
            "candidates": [],
        }

        critic_tiles: list[tuple[str, Image.Image, Image.Image, Image.Image]] = []
        for candidate_id, candidate, construction in candidate_masks:
            candidate_dir = out_root / candidate_id
            candidate_dir.mkdir(parents=True, exist_ok=False)
            mask_path = candidate_dir / "repaired_object_mask.png"
            rgb_path = candidate_dir / "hunyuan_input_rgb.png"
            overlay_path = candidate_dir / "repaired_object_mask_overlay.png"
            part_overlay_path = candidate_dir / "part_and_distractor_overlay.png"
            manifest_path = candidate_dir / "candidate_manifest.json"

            mask_image = Image.fromarray(candidate.astype(np.uint8) * 255, mode="L")
            mask_image.save(mask_path)
            white = np.full_like(context, 255)
            white[candidate] = context[candidate]
            Image.fromarray(white).save(rgb_path)

            green = np.zeros_like(reference)
            green[:, :, 1] = 255
            alpha = candidate.astype(np.float32)[..., None] * 0.45
            overlay = (reference * (1.0 - alpha) + green * alpha).clip(0, 255).astype(np.uint8)
            Image.fromarray(overlay).save(overlay_path)

            parts = reference.astype(np.float32)
            layers = [
                (lid, np.array([0, 255, 0], dtype=np.float32)),
                (base, np.array([0, 160, 255], dtype=np.float32)),
                (support, np.array([255, 0, 0], dtype=np.float32)),
                (tabletop, np.array([255, 0, 255], dtype=np.float32)),
            ]
            for layer_mask, color in layers:
                layer_alpha = layer_mask.astype(np.float32)[..., None] * 0.28
                parts = parts * (1.0 - layer_alpha) + color * layer_alpha
            Image.fromarray(parts.clip(0, 255).astype(np.uint8)).save(part_overlay_path)

            pixels = int(candidate.sum())
            components, largest_fraction = component_stats(candidate)
            lid_retention = int((candidate & lid).sum()) / max(1, int(lid.sum()))
            base_retention = int((candidate & base).sum()) / max(1, int(base.sum()))
            support_overlap = int((candidate & support).sum()) / max(1, pixels)
            table_overlap = int((candidate & tabletop).sum()) / max(1, pixels)
            bottom_touch = int(candidate[-2:, :].sum()) / max(1, pixels)
            lid_center = centroid(candidate & lid)
            base_center = centroid(candidate & base)
            lid_above_base = bool(
                lid_center is not None and base_center is not None and lid_center[1] < base_center[1]
            )
            hinge_connected = bool(
                (dilate(candidate & lid, hinge_dilation_px) & dilate(candidate & base, hinge_dilation_px)).any()
            )
            gate_pass = bool(
                pixels > min_pixels
                and 1 <= components <= max_components
                and largest_fraction >= 0.85
                and lid_retention >= min_lid_retention
                and base_retention >= min_base_retention
                and support_overlap <= max_distractor_overlap
                and table_overlap <= max_distractor_overlap
                and bottom_touch <= max_border_touch
                and lid_above_base
                and hinge_connected
            )

            metrics = {
                "foreground_pixels": pixels,
                "components": components,
                "largest_component_fraction": largest_fraction,
                "lid_retention": lid_retention,
                "base_retention": base_retention,
                "support_overlap_fraction": support_overlap,
                "tabletop_overlap_fraction": table_overlap,
                "bottom_border_touch_fraction": bottom_touch,
                "lid_above_base": lid_above_base,
                "hinge_connected_with_dilation": hinge_connected,
                "deterministic_gate_pass": gate_pass,
            }
            manifest = {
                "schema_version": "inpaint_fallback_candidate_v7_auto_part_graph",
                "case_id": case_id,
                "candidate_id": candidate_id,
                "scientific_role": "automatic_candidate",
                "eligible_for_main_automatic_result": True,
                "construction": construction,
                "manual_geometry_used": False,
                "candidate_I_pixels_or_coordinates_used": False,
                "source_context": str(context_path),
                "source_context_sha256": digest(context_path),
                "cleaned_mask": str(mask_path),
                "cleaned_mask_sha256": digest(mask_path),
                "hunyuan_input_rgb": str(rgb_path),
                "hunyuan_input_rgb_sha256": digest(rgb_path),
                "overlay": str(overlay_path),
                "metrics": metrics,
            }
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            summary["candidates"].append({
                "candidate_id": candidate_id,
                "candidate_dir": str(candidate_dir),
                "manifest": str(manifest_path),
                "mask": str(mask_path),
                "hunyuan_input_rgb": str(rgb_path),
                "overlay": str(overlay_path),
                "deterministic_gate_pass": gate_pass,
                "metrics": metrics,
            })
            critic_tiles.append((
                candidate_id,
                Image.open(overlay_path).convert("RGB"),
                Image.open(mask_path).convert("RGB"),
                Image.open(rgb_path).convert("RGB"),
            ))
            status = "PASS" if gate_pass else "HOLD"
            print(f"[{status}] AUTO_V2_CANDIDATE={candidate_id}")

        summary_path = out_root / "candidate_bank_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

        # Contact sheet: columns are candidates, rows are overlay/mask/RGB.
        tile_w = min(512, width)
        tile_h = round(tile_w * height / width)
        label_h = 28
        sheet_w = tile_w * len(critic_tiles)
        sheet_h = label_h + tile_h * 3
        sheet = Image.new("RGB", (sheet_w, sheet_h), "white")
        draw = ImageDraw.Draw(sheet)
        for index, (candidate_id, overlay_img, mask_img, rgb_img) in enumerate(critic_tiles):
            x = index * tile_w
            draw.rectangle((x, 0, x + tile_w, label_h), fill=(245, 245, 245))
            draw.text((x + 5, 6), candidate_id, fill=(0, 0, 0))
            sheet.paste(overlay_img.resize((tile_w, tile_h)), (x, label_h))
            sheet.paste(mask_img.resize((tile_w, tile_h)), (x, label_h + tile_h))
            sheet.paste(rgb_img.resize((tile_w, tile_h)), (x, label_h + tile_h * 2))
        contact_sheet = out_root / "critic_candidate_bank.png"
        sheet.save(contact_sheet)

        print(f"[PASS] AUTO_V2_CANDIDATE_BANK={summary_path}")
        print(f"[PASS] AUTO_V2_CRITIC_PANEL={contact_sheet}")
    except Exception as error:
        print(f"[HOLD] CANDIDATE_BANK_FAILED={type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
