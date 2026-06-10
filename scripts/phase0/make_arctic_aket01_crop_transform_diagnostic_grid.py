from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

SPLIT = Path("/home/fredcui/Projects/arctic/unpack/arctic_data/data/splits/p1_train.npy")
IMG = Path("/home/fredcui/foho_phase0/inputs/arctic_phase017/aket01.jpg")
OUT = Path.home() / "foho_phase0/inspection/arctic_phase017/gt_overlay_aket01/aket01_crop_transform_diagnostic_grid.jpg"

SEQ = "s01/ketchup_grab_01"
FRAME = 147
VIEW = 7
OUT_SIZE = 1000

data = np.load(SPLIT, allow_pickle=True).item()
seq = data["data_dict"][SEQ]

bbox = seq["bbox"][FRAME, VIEW].astype(np.float32)
center = bbox[:2]
scale = float(bbox[2])

points = {
    "right": seq["2d"]["joints.right"][FRAME, VIEW],
    "left": seq["2d"]["joints.left"][FRAME, VIEW],
    "obj": seq["2d"]["kp3d"][FRAME, VIEW],
    "bbox": seq["2d"]["bbox3d"][FRAME, VIEW],
}

def make_overlay(side, title):
    img = Image.open(IMG).convert("RGB")
    draw = ImageDraw.Draw(img)
    top_left = center - side / 2.0

    def convert(p):
        return (p - top_left[None, :]) * (OUT_SIZE / side)

    colors = {
        "right": "red",
        "left": "lime",
        "obj": "cyan",
        "bbox": "yellow",
    }

    inside_total = 0
    count_total = 0

    for name, pts in points.items():
        q = convert(np.asarray(pts, dtype=np.float32))
        for x, y in q:
            if 0 <= x < OUT_SIZE and 0 <= y < OUT_SIZE:
                inside_total += 1
            count_total += 1
            draw.ellipse((x-4, y-4, x+4, y+4), outline=colors[name], width=2)

    draw.text((15, 15), f"{title} | inside {inside_total}/{count_total}", fill="white")
    return img

candidates = [
    ("side = scale * 200", scale * 200.0),
    ("side = scale", scale),
    ("side = scale * 100", scale * 100.0),
    ("side = scale * 150", scale * 150.0),
]

tiles = [make_overlay(side, title) for title, side in candidates]

grid = Image.new("RGB", (2000, 2000), "black")
for idx, tile in enumerate(tiles):
    tile = tile.resize((1000, 1000))
    x = (idx % 2) * 1000
    y = (idx // 2) * 1000
    grid.paste(tile, (x, y))

OUT.parent.mkdir(parents=True, exist_ok=True)
grid.save(OUT)
print("[OK] wrote", OUT)
print("bbox:", bbox, "center:", center, "scale:", scale)
