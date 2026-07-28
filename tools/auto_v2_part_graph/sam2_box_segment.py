#!/usr/bin/env python3
"""Run box-prompted SAM2 masks from a validated spatial proposal.

Usage:
  python3 sam2_box_segment.py BOXES_PX.json IMAGE.png MODEL_CONFIG CHECKPOINT OUTPUT_DIR [DEVICE]

MODEL_CONFIG should be the config identifier/path accepted by the installed SAM2 build.
The script avoids argparse/SystemExit(2) and prints HOLD markers on incompatibility.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sys


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if len(sys.argv) not in (6, 7):
        print(
            "[HOLD] SAM2_BOX_USAGE="
            "BOXES_PX.json IMAGE.png MODEL_CONFIG CHECKPOINT OUTPUT_DIR [DEVICE]"
        )
        return

    boxes_path = Path(sys.argv[1])
    image_path = Path(sys.argv[2])
    model_config = sys.argv[3]
    checkpoint = Path(sys.argv[4])
    out_dir = Path(sys.argv[5])
    device = sys.argv[6] if len(sys.argv) == 7 else "cuda"

    if not boxes_path.is_file() or not image_path.is_file() or not checkpoint.is_file():
        print(
            "[HOLD] SAM2_BOX_INPUT_MISSING="
            f"boxes={boxes_path.is_file()} image={image_path.is_file()} "
            f"checkpoint={checkpoint.is_file()}"
        )
        return

    try:
        import numpy as np
        from PIL import Image
        import torch
        from sam2.build_sam import build_sam2
        from sam2.sam2_image_predictor import SAM2ImagePredictor
    except Exception as error:  # pragma: no cover - depends on desktop env
        print(f"[HOLD] SAM2_IMPORT_FAILED={type(error).__name__}: {error}")
        return

    if out_dir.exists() and any(out_dir.iterdir()):
        print(f"[HOLD] SAM2_OUTPUT_NOT_EMPTY={out_dir}")
        return
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        payload = json.loads(boxes_path.read_text(encoding="utf-8"))
        regions = payload["regions"]
        image = Image.open(image_path).convert("RGB")
        image_np = np.asarray(image)

        if device.startswith("cuda") and not torch.cuda.is_available():
            print("[HOLD] SAM2_CUDA_UNAVAILABLE")
            return

        model = build_sam2(model_config, str(checkpoint), device=device)
        predictor = SAM2ImagePredictor(model)
        predictor.set_image(image_np)

        palette = {
            "whole_laptop": np.array([255, 255, 0], dtype=np.uint8),
            "laptop_lid": np.array([0, 255, 0], dtype=np.uint8),
            "laptop_base": np.array([0, 160, 255], dtype=np.uint8),
            "wooden_support": np.array([255, 0, 0], dtype=np.uint8),
            "tabletop": np.array([255, 0, 255], dtype=np.uint8),
        }
        summary = {
            "schema_version": "auto_v2_sam2_box_masks_v1",
            "case_id": "alapuse02v3n60",
            "source_image": str(image_path),
            "source_image_sha256": digest(image_path),
            "boxes": str(boxes_path),
            "boxes_sha256": digest(boxes_path),
            "model_config": model_config,
            "checkpoint": str(checkpoint),
            "checkpoint_sha256": digest(checkpoint),
            "device": device,
            "masks": {},
        }

        for label, item in regions.items():
            box = np.asarray(item["box_px_xyxy"], dtype=np.float32)
            masks, scores, _ = predictor.predict(
                point_coords=None,
                point_labels=None,
                box=box,
                multimask_output=True,
            )
            masks_np = np.asarray(masks)
            scores_np = np.asarray(scores).reshape(-1)
            if masks_np.ndim == 2:
                masks_np = masks_np[None, ...]
            if len(scores_np) != len(masks_np):
                scores_np = np.ones((len(masks_np),), dtype=np.float32)
            index = int(scores_np.argmax())
            mask = masks_np[index].astype(bool)
            pixels = int(mask.sum())
            if pixels < 50:
                print(f"[HOLD] SAM2_MASK_TOO_SMALL={label}:{pixels}")
                return

            mask_path = out_dir / f"{label}_mask.png"
            overlay_path = out_dir / f"{label}_overlay.png"
            Image.fromarray(mask.astype(np.uint8) * 255, mode="L").save(mask_path)

            overlay = image_np.astype(np.float32)
            color = palette.get(label, np.array([0, 255, 255], dtype=np.uint8))
            alpha = mask.astype(np.float32)[..., None] * 0.45
            overlay = (overlay * (1.0 - alpha) + color * alpha).clip(0, 255).astype(np.uint8)
            Image.fromarray(overlay).save(overlay_path)

            summary["masks"][label] = {
                "mask": str(mask_path),
                "mask_sha256": digest(mask_path),
                "overlay": str(overlay_path),
                "score": float(scores_np[index]),
                "foreground_pixels": pixels,
            }
            print(f"[PASS] SAM2_MASK={label}:{mask_path}")

        summary_path = out_dir / "segmentation_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"[PASS] SAM2_SUMMARY={summary_path}")
    except Exception as error:
        print(f"[HOLD] SAM2_BOX_SEGMENT_FAILED={type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
