from pathlib import Path
import numpy as np
from PIL import Image

SPLIT = Path("/home/fredcui/Projects/arctic/unpack/arctic_data/data/splits/p1_train.npy")

ORIG = Path("/home/fredcui/Projects/arctic/data/arctic_data/data/images/s01/ketchup_grab_01/7/00147.jpg")
CROP1 = Path("/home/fredcui/Projects/arctic/data/cropped_images/s01/ketchup_grab_01/7/00147.jpg")
CROP2 = Path("/home/fredcui/Projects/arctic/data/cropped_images_structured/s01/ketchup_grab_01/7/00147.jpg")
INPUT = Path("/home/fredcui/foho_phase0/inputs/arctic_phase017/aket01.jpg")

SEQ = "s01/ketchup_grab_01"
FRAME = 147
VIEW = 7

data = np.load(SPLIT, allow_pickle=True).item()
seq = data["data_dict"][SEQ]

print("===== image sizes =====")
for name, p in [
    ("original", ORIG),
    ("cropped_images", CROP1),
    ("cropped_images_structured", CROP2),
    ("phase017_input", INPUT),
]:
    if p.exists():
        img = Image.open(p)
        print(f"{name:25s}", img.size, p)
    else:
        print(f"{name:25s}", "[MISS]", p)

print("\n===== bbox from split =====")
bbox = seq["bbox"][FRAME, VIEW]
print("bbox shape:", bbox.shape)
print("bbox value:", bbox)
print("common meaning is usually [center_x, center_y, scale]")

print("\n===== 2D coordinate ranges from split =====")
for name, pts in [
    ("joints.right", seq["2d"]["joints.right"][FRAME, VIEW]),
    ("joints.left", seq["2d"]["joints.left"][FRAME, VIEW]),
    ("kp3d", seq["2d"]["kp3d"][FRAME, VIEW]),
    ("bbox3d", seq["2d"]["bbox3d"][FRAME, VIEW]),
]:
    pts = np.asarray(pts)
    print(f"{name:15s}", "shape", pts.shape, "min", pts.min(axis=0), "max", pts.max(axis=0))
