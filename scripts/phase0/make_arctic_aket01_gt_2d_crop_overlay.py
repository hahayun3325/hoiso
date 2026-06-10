from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SPLIT = Path("/home/fredcui/Projects/arctic/unpack/arctic_data/data/splits/p1_train.npy")
IMG = Path("/home/fredcui/foho_phase0/inputs/arctic_phase017/aket01.jpg")
OUT = Path.home() / "foho_phase0/inspection/arctic_phase017/gt_overlay_aket01/aket01_gt_2d_crop_overlay.jpg"

SEQ = "s01/ketchup_grab_01"
FRAME = 147
VIEW = 7
OUT_SIZE = 1000

data = np.load(SPLIT, allow_pickle=True).item()
seq = data["data_dict"][SEQ]

bbox = seq["bbox"][FRAME, VIEW].astype(np.float32)
center = bbox[:2]
scale = float(bbox[2])

# ARCTIC follows common HMR-style convention: crop_side = scale * 200.
crop_side = scale * 200.0
top_left = center - crop_side / 2.0

print("image:", IMG)
print("bbox:", bbox)
print("center:", center)
print("scale:", scale)
print("crop_side:", crop_side)
print("top_left:", top_left)

def original_to_crop(points):
    points = np.asarray(points, dtype=np.float32)
    out = (points - top_left[None, :]) * (OUT_SIZE / crop_side)
    return out

img = Image.open(IMG).convert("RGB")
draw = ImageDraw.Draw(img)
W, H = img.size
print("input image size:", W, H)

def draw_points(points_orig, color, radius=5, name="points"):
    points_crop = original_to_crop(points_orig)
    inside = 0

    print("\n" + name)
    print("original min/max:", points_orig.min(axis=0), points_orig.max(axis=0))
    print("crop min/max:", points_crop.min(axis=0), points_crop.max(axis=0))

    for x, y in points_crop:
        if np.isfinite(x) and np.isfinite(y):
            if 0 <= x < W and 0 <= y < H:
                inside += 1
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), outline=color, width=3)

    print("inside crop:", inside, "/", len(points_crop))
    return points_crop

j2d_r = seq["2d"]["joints.right"][FRAME, VIEW]
j2d_l = seq["2d"]["joints.left"][FRAME, VIEW]
kp2d = seq["2d"]["kp3d"][FRAME, VIEW]
bbox2d = seq["2d"]["bbox3d"][FRAME, VIEW]

r_crop = draw_points(j2d_r, "red", 5, "right hand joints")
l_crop = draw_points(j2d_l, "lime", 5, "left hand joints")
k_crop = draw_points(kp2d, "cyan", 4, "object keypoints")
b_crop = draw_points(bbox2d, "yellow", 4, "object bbox3d projected points")

# Draw bbox connections approximately.
if len(b_crop) >= 8:
    edges = [
        (0,1),(1,2),(2,3),(3,0),
        (4,5),(5,6),(6,7),(7,4),
        (0,4),(1,5),(2,6),(3,7),
    ]
    for i, j in edges:
        x1, y1 = b_crop[i]
        x2, y2 = b_crop[j]
        draw.line((x1, y1, x2, y2), fill="yellow", width=2)

draw.text((20, 20), "red=right hand, green=left hand, cyan=obj keypoints, yellow=obj bbox", fill="white")

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print("\n[OK] wrote", OUT)
