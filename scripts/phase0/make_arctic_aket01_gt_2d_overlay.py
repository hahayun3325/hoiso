from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

SPLIT = Path("/home/fredcui/Projects/arctic/unpack/arctic_data/data/splits/p1_train.npy")
IMG = Path("/home/fredcui/foho_phase0/inputs/arctic_phase017/aket01.jpg")
OUT = Path.home() / "foho_phase0/inspection/arctic_phase017/gt_overlay_aket01/aket01_gt_2d_overlay.jpg"

SEQ = "s01/ketchup_grab_01"
FRAME = 147
VIEW = 7

data = np.load(SPLIT, allow_pickle=True).item()
seq = data["data_dict"][SEQ]

img = Image.open(IMG).convert("RGB")
draw = ImageDraw.Draw(img)

W, H = img.size
print("image:", IMG)
print("image size:", W, H)

def draw_points(points, color, radius=4, name="points"):
    points = np.asarray(points)
    print(name, "shape:", points.shape, "min:", points.min(axis=0), "max:", points.max(axis=0))
    inside = 0
    for x, y in points:
        if np.isfinite(x) and np.isfinite(y):
            if 0 <= x < W and 0 <= y < H:
                inside += 1
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), outline=color, width=2)
    print(name, "inside image:", inside, "/", len(points))

j2d_r = seq["2d"]["joints.right"][FRAME, VIEW]
j2d_l = seq["2d"]["joints.left"][FRAME, VIEW]
bbox2d = seq["2d"]["bbox3d"][FRAME, VIEW]
kp2d = seq["2d"]["kp3d"][FRAME, VIEW]

draw_points(j2d_r, "red", 4, "right hand joints")
draw_points(j2d_l, "lime", 4, "left hand joints")
draw_points(kp2d, "cyan", 3, "object keypoints")
draw_points(bbox2d, "yellow", 3, "object bbox3d projected points")

# connect simple bbox edges if 16 points are available
if len(bbox2d) >= 8:
    for i in range(8):
        x1, y1 = bbox2d[i]
        x2, y2 = bbox2d[(i + 1) % 8]
        draw.line((x1, y1, x2, y2), fill="yellow", width=2)

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print("[OK] wrote", OUT)
