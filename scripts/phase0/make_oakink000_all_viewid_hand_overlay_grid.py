from pathlib import Path
from PIL import Image, ImageDraw
import pickle
import numpy as np
import os

OAK = Path(os.environ["OAKINK_DIR"]).resolve()
IMG_DIR = OAK / "image/stream_release_v2/A01023_0001_0002/2021-10-12-17-13-00"
ROOT = Path.home() / "foho_phase0/inspection/oakink_000/gt_assets/oakink_image_annotation/frame90/anno"
OUT = Path.home() / "foho_phase0/inspection/oakink_000/oakink000_all_viewid_hand_overlay_grid.jpg"
CHECK = OUT.with_suffix(".source_check.txt")

SEQ = "A01023_0001_0002__2021-10-12-17-13-00__0__90"
VIEW_NAMES = ["south_east", "south_west", "north_east", "north_west"]

def load_pkl(p):
    with open(p, "rb") as f:
        return pickle.load(f)

def project(points, K):
    pts = np.asarray(points, dtype=np.float64)
    z = pts[:, 2]
    good = z > 1e-6
    pts = pts[good]
    z = z[good]
    u = K[0,0] * pts[:,0] / z + K[0,2]
    v = K[1,1] * pts[:,1] / z + K[1,2]
    return np.stack([u, v], axis=1)

def draw_points(img, pts2d, color, radius=2, max_points=700):
    d = ImageDraw.Draw(img)
    pts = np.asarray(pts2d)
    if len(pts) > max_points:
        idx = np.linspace(0, len(pts)-1, max_points).astype(int)
        pts = pts[idx]
    for x, y in pts:
        if 0 <= x < img.width and 0 <= y < img.height:
            d.ellipse([x-radius, y-radius, x+radius, y+radius], fill=color)

def make_cell(view_name, view_id):
    img_path = IMG_DIR / f"{view_name}_color_90.png"
    raw = Image.open(img_path).convert("RGB")
    W0, H0 = raw.width, raw.height

    raw.thumbnail((260, 190))
    sx, sy = raw.width / W0, raw.height / H0

    suffix = f"{SEQ}__{view_id}.pkl"
    hand_v = np.asarray(load_pkl(ROOT / "hand_v" / suffix))
    hand_j = np.asarray(load_pkl(ROOT / "hand_j" / suffix))
    K = np.asarray(load_pkl(ROOT / "cam_intr" / suffix), dtype=np.float64)

    v2d = project(hand_v, K)
    j2d = project(hand_j, K)
    v2d[:,0] *= sx
    v2d[:,1] *= sy
    j2d[:,0] *= sx
    j2d[:,1] *= sy

    draw_points(raw, v2d, (255, 0, 0), radius=1)
    draw_points(raw, j2d, (0, 255, 0), radius=3, max_points=21)

    cell = Image.new("RGB", (280, 235), (245,245,245))
    d = ImageDraw.Draw(cell)
    d.text((8, 8), f"{view_name} image", fill=(0,0,0))
    d.text((8, 26), f"anno view_id={view_id}", fill=(80,80,80))
    cell.paste(raw, ((280-raw.width)//2, 42))
    return cell

cols = 4
rows = 4
canvas = Image.new("RGB", (cols*280, rows*235), (230,230,230))

for r, view_name in enumerate(VIEW_NAMES):
    for c, view_id in enumerate(range(4)):
        canvas.paste(make_cell(view_name, view_id), (c*280, r*235))

OUT.parent.mkdir(parents=True, exist_ok=True)
canvas.save(OUT, quality=95)
CHECK.write_text(
    "Rows=image view name. Columns=annotation view id.\n"
    "Correct mapping is where red/green hand overlay matches the hand in that row.\n"
)
print("[OK] wrote", OUT)
print("[OK] wrote", CHECK)
