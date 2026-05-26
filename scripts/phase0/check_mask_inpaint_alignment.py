from pathlib import Path
from PIL import Image
import numpy as np

base = Path.home() / "foho_phase0/runs/smoke_015_prompt_rect"

img_path = base / "ours_inpaint/test_inpainted_object.png"
mask_path = base / "cropped_hand_masks/test_cropped_obj_mask.png"
crop_path = base / "cropped_hoi_imgs/test_cropped_hoi_1.png"

out_dir = Path.home() / "foho_phase0/inspection/prompt_ablation"
out_dir.mkdir(parents=True, exist_ok=True)

for p in [img_path, mask_path, crop_path]:
    print(p, "exists:", p.exists())

if not (img_path.exists() and mask_path.exists()):
    raise SystemExit("[BAD] missing image or mask")

img = Image.open(img_path).convert("RGB")
mask = Image.open(mask_path).convert("L")

print("inpaint size:", img.size)
print("mask size:", mask.size)

if mask.size != img.size:
    print("[WARN] resizing mask from", mask.size, "to", img.size)
    mask = mask.resize(img.size, Image.NEAREST)

img_np = np.array(img)
mask_np = np.array(mask) > 127

overlay = img_np.copy()
overlay[mask_np] = (0.55 * overlay[mask_np] + 0.45 * np.array([255, 0, 0])).astype(np.uint8)

out_path = out_dir / "smoke015_inpaint_objmask_overlay.jpg"
Image.fromarray(overlay).save(out_path, quality=95)

ys, xs = np.where(mask_np)
bbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(xs) else None

print("mask area:", int(mask_np.sum()))
print("mask bbox:", bbox)
print("[OK] wrote", out_path)
