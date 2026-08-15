from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit_v1_getting_unstuck"
RUN_ROOT = Path("/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_alapuse01_partaware_v2/attempt0_partaware_prompt/run_outputs/arctic_alapuse01_partaware_v2_attempt0")

img_path = RUN_ROOT / "cropped_hoi_imgs/alapuse01_cropped_hoi_1.png"
obj_mask_path = RUN_ROOT / "cropped_hand_masks/alapuse01_cropped_obj_mask.png"

out_lid = FIT / "inputs/alapuse01_lid_mask_coarse_v1.png"
out_base = FIT / "inputs/alapuse01_base_mask_coarse_v1.png"
out_overlay = FIT / "visuals/alapuse01_lid_base_mask_overlay_coarse_v1.png"
out_meta = FIT / "metrics/coarse_lid_base_mask_v1_report.json"

img = Image.open(img_path).convert("RGB")
obj = np.asarray(Image.open(obj_mask_path).convert("L")) > 127
H, W = obj.shape

ys, xs = np.where(obj)
if len(xs) == 0:
    raise ValueError("empty object mask")

# Coarse split: upper object pixels become lid/screen; lower object pixels become base.
# This is only a bootstrap. Inspect overlay before trusting it.
y_min, y_max = int(ys.min()), int(ys.max())
x_min, x_max = int(xs.min()), int(xs.max())

split_y = int(y_min + 0.48 * (y_max - y_min))

lid = obj & (np.indices((H, W))[0] <= split_y)
base = obj & (np.indices((H, W))[0] > split_y)

Image.fromarray((lid.astype(np.uint8) * 255)).save(out_lid)
Image.fromarray((base.astype(np.uint8) * 255)).save(out_base)

overlay = img.copy().convert("RGBA")
lid_layer = Image.new("RGBA", (W, H), (0, 255, 255, 0))
base_layer = Image.new("RGBA", (W, H), (255, 0, 255, 0))

lid_rgba = np.zeros((H, W, 4), dtype=np.uint8)
lid_rgba[lid] = [0, 255, 255, 100]
base_rgba = np.zeros((H, W, 4), dtype=np.uint8)
base_rgba[base] = [255, 0, 255, 100]

overlay = Image.alpha_composite(overlay, Image.fromarray(lid_rgba))
overlay = Image.alpha_composite(overlay, Image.fromarray(base_rgba))

draw = ImageDraw.Draw(overlay)
draw.line([(0, split_y), (W, split_y)], fill=(255, 255, 0, 255), width=2)
overlay.convert("RGB").save(out_overlay)

report = {
    "method": "coarse_y_split_object_mask",
    "warning": "bootstrap mask only; inspect overlay before fitting",
    "image": str(img_path),
    "object_mask": str(obj_mask_path),
    "lid_mask": str(out_lid),
    "base_mask": str(out_base),
    "overlay": str(out_overlay),
    "bbox": [x_min, y_min, x_max, y_max],
    "split_y": split_y,
    "lid_pixels": int(lid.sum()),
    "base_pixels": int(base.sum())
}

out_meta.write_text(json.dumps(report, indent=2))

print("[OK] wrote", out_lid)
print("[OK] wrote", out_base)
print("[OK] wrote", out_overlay)
print(json.dumps(report, indent=2))
