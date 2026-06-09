from pathlib import Path
from PIL import Image, ImageDraw
import pickle
import numpy as np
import os

OAK = Path(os.environ["OAKINK_DIR"]).resolve()
IMG = OAK / "image/stream_release_v2/A01023_0001_0002/2021-10-12-17-13-00/south_east_color_90.png"

ROOT = Path.home() / "foho_phase0/inspection/oakink_000/gt_assets/oakink_image_annotation/frame90/anno"
OUT = Path.home() / "foho_phase0/inspection/oakink_000/oakink000_south_east_viewid_hand_overlay.jpg"
CHECK = OUT.with_suffix(".source_check.txt")

SEQ = "A01023_0001_0002__2021-10-12-17-13-00__0__90"

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

def draw_points(img, pts2d, color, radius=2, max_points=900):
    d = ImageDraw.Draw(img)
    pts = np.asarray(pts2d)
    if len(pts) > max_points:
        idx = np.linspace(0, len(pts)-1, max_points).astype(int)
        pts = pts[idx]
    for x, y in pts:
        if 0 <= x < img.width and 0 <= y < img.height:
            d.ellipse([x-radius, y-radius, x+radius, y+radius], fill=color)

def make_card(view_id):
    base = Image.open(IMG).convert("RGB")
    base.thumbnail((420, 320))
    scale_x = base.width / Image.open(IMG).width
    scale_y = base.height / Image.open(IMG).height

    suffix = f"{SEQ}__{view_id}.pkl"
    hand_v = np.asarray(load_pkl(ROOT / "hand_v" / suffix))
    hand_j = np.asarray(load_pkl(ROOT / "hand_j" / suffix))
    K = np.asarray(load_pkl(ROOT / "cam_intr" / suffix), dtype=np.float64)

    v2d = project(hand_v, K)
    j2d = project(hand_j, K)
    v2d[:,0] *= scale_x
    v2d[:,1] *= scale_y
    j2d[:,0] *= scale_x
    j2d[:,1] *= scale_y

    draw_points(base, v2d, color=(255, 30, 30), radius=1)
    draw_points(base, j2d, color=(30, 255, 30), radius=4, max_points=21)

    card = Image.new("RGB", (450, 380), (245,245,245))
    d = ImageDraw.Draw(card)
    d.text((10, 10), f"south_east image + annotation view_id={view_id}", fill=(0,0,0))
    d.text((10, 30), "red=hand vertices, green=joints", fill=(80,80,80))
    card.paste(base, ((450-base.width)//2, 55))
    return card

cards = [make_card(i) for i in range(4)]

canvas = Image.new("RGB", (900, 760), (230,230,230))
canvas.paste(cards[0], (0,0))
canvas.paste(cards[1], (450,0))
canvas.paste(cards[2], (0,380))
canvas.paste(cards[3], (450,380))

OUT.parent.mkdir(parents=True, exist_ok=True)
canvas.save(OUT, quality=95)

CHECK.write_text(
    f"image={IMG}\n"
    + "\n".join([f"view_id={i}: {ROOT/'hand_v'/(SEQ+'__'+str(i)+'.pkl')}" for i in range(4)])
)

print("[OK] wrote", OUT)
print("[OK] wrote", CHECK)
