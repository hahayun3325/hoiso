from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit_v1_getting_unstuck"
RUN_ROOT = Path("/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_alapuse01_partaware_v2/attempt0_partaware_prompt/run_outputs/arctic_alapuse01_partaware_v2_attempt0")

img_path = RUN_ROOT / "cropped_hoi_imgs/alapuse01_cropped_hoi_1.png"
poly_path = FIT / "inputs/manual_lid_base_polygons_v1.json"

out_lid = FIT / "inputs/alapuse01_lid_mask_manual_v1.png"
out_base = FIT / "inputs/alapuse01_base_mask_manual_v1.png"
out_overlay = FIT / "visuals/alapuse01_lid_base_mask_overlay_manual_v1.png"
out_report = FIT / "metrics/manual_lid_base_mask_v1_report.json"

img = Image.open(img_path).convert("RGB")
W, H = img.size

poly = json.loads(poly_path.read_text())

def polygon_mask(points):
    m = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(m)
    draw.polygon([tuple(p) for p in points], fill=255)
    return m

lid = polygon_mask(poly["lid_outer_surface"])
base = polygon_mask(poly["keyboard_base"])

lid.save(out_lid)
base.save(out_base)

lid_np = np.asarray(lid) > 127
base_np = np.asarray(base) > 127

overlay = img.convert("RGBA")

lid_rgba = np.zeros((H, W, 4), dtype=np.uint8)
lid_rgba[lid_np] = [0, 255, 255, 105]

base_rgba = np.zeros((H, W, 4), dtype=np.uint8)
base_rgba[base_np] = [255, 0, 255, 105]

overlay = Image.alpha_composite(overlay, Image.fromarray(lid_rgba))
overlay = Image.alpha_composite(overlay, Image.fromarray(base_rgba))

draw = ImageDraw.Draw(overlay)
draw.line([tuple(p) for p in poly["lid_outer_surface"] + [poly["lid_outer_surface"][0]]], fill=(0, 255, 255, 255), width=2)
draw.line([tuple(p) for p in poly["keyboard_base"] + [poly["keyboard_base"][0]]], fill=(255, 0, 255, 255), width=2)

overlay.convert("RGB").save(out_overlay)

report = {
    "case_id": "alapuse01",
    "method": "manual_polygon_masks_v1",
    "image": str(img_path),
    "polygon_json": str(poly_path),
    "lid_mask": str(out_lid),
    "base_mask": str(out_base),
    "overlay": str(out_overlay),
    "lid_pixels": int(lid_np.sum()),
    "base_pixels": int(base_np.sum()),
    "decision": "VISUAL_CHECK_REQUIRED"
}

out_report.write_text(json.dumps(report, indent=2))

print("[OK] wrote", out_lid)
print("[OK] wrote", out_base)
print("[OK] wrote", out_overlay)
print(json.dumps(report, indent=2))
