from pathlib import Path
from PIL import Image
import numpy as np

input_path = Path.home() / "foho_phase0/inputs/test_hoi_clean_002.jpg"
ho3d_root = Path("/home/fredcui/Projects/holdse/generator/assets/ho3d_v3/train")

if not input_path.exists():
    raise SystemExit(f"[MISSING] {input_path}")

def thumb(path):
    im = Image.open(path).convert("RGB").resize((64, 64))
    return np.asarray(im).astype(np.float32) / 255.0

query = thumb(input_path)

candidates = []
for p in ho3d_root.glob("*/rgb/*.jpg"):
    try:
        arr = thumb(p)
        mse = float(np.mean((query - arr) ** 2))
        candidates.append((mse, p))
    except Exception:
        pass

candidates.sort(key=lambda x: x[0])

out = Path.home() / "foho_phase0/inspection/input_nearest_ho3d_matches.txt"
with out.open("w") as f:
    for mse, p in candidates[:30]:
        line = f"{mse:.8f}\t{p}\n"
        print(line, end="")
        f.write(line)

print("[OK] wrote", out)
