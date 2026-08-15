from pathlib import Path
import hashlib
import os
import pandas as pd
from PIL import Image

run = Path.home() / "foho_phase0/runs/oakink_000_baseline"
config = Path("configs/pipeline.phase0.oakink000.env")
split = pd.read_csv("test_splits/oakink_test.csv").iloc[0]

def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def img_info(path):
    p = Path(path)
    if not p.exists():
        return {"exists": False}
    im = Image.open(p)
    return {
        "exists": True,
        "path": str(p),
        "size": im.size,
        "md5": md5(p),
    }

print("===== config lines =====")
for line in config.read_text().splitlines():
    if any(k in line for k in ["BASE_DIR", "IMAGE_PATH", "GEMINI_API_KEY", "FOHO_DEBUG_DIR"]):
        print(line)

print("\n===== split row 0 =====")
print(split.to_dict())

print("\n===== run images =====")
for name, path in {
    "copied_input": Path.home() / "foho_phase0/inputs/oakink/oakink_split000.png",
    "run_original": run / "original_imgs/oakink_full_image_1.png",
    "crop": run / "cropped_hoi_imgs/oakink_cropped_hoi_1.png",
    "inpaint": run / "ours_inpaint/oakink_inpainted_object.png",
    "obj_mask": run / "cropped_hand_masks/oakink_cropped_obj_mask.png",
}.items():
    print(name, img_info(path))

print("\n===== run meshes =====")
for p in sorted(run.glob("**/*.ply")):
    print(p)

print("\n===== warning check =====")
bad = []
for p in sorted(run.glob("**/*")):
    s = str(p)
    if "smoke022" in s or "smoke_022" in s or "test_hoi_clean" in s:
        bad.append(s)
print("bad_path_count:", len(bad))
for x in bad:
    print(x)
