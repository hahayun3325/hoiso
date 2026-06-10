from pathlib import Path
import sys
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

ARCTIC_ROOT = Path("/home/fredcui/Projects/arctic")
sys.path.insert(0, str(ARCTIC_ROOT))

from common.data_utils import transform

SPLIT = Path("/home/fredcui/Projects/arctic/unpack/arctic_data/data/splits/p1_train.npy")
CASES = Path("/home/fredcui/Projects/FollowMyHold/docs/phase0/arctic_phase017_selected_cases.csv")
OUT_DIR = Path.home() / "foho_phase0/inspection/arctic_phase017/gt_overlay_all_cases"
RES = [1000, 1000]

data = np.load(SPLIT, allow_pickle=True).item()
df = pd.read_csv(CASES)

OUT_DIR.mkdir(parents=True, exist_ok=True)

def official_to_crop(points, center, scale):
    out = []
    for p in np.asarray(points, dtype=np.float32):
        out.append(transform(p, center, scale, RES, invert=0, rot=0))
    return np.asarray(out, dtype=np.float32)

def draw_points(draw, points, color, radius=4):
    for x, y in points:
        if np.isfinite(x) and np.isfinite(y):
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), outline=color, width=2)

def count_inside(points, w, h):
    pts = np.asarray(points)
    return int(((pts[:, 0] >= 0) & (pts[:, 0] < w) & (pts[:, 1] >= 0) & (pts[:, 1] < h)).sum())

summary = []

for _, row in df.iterrows():
    case = row["case"]
    seq = f'{row["subject"]}/{row["seq_name"]}'
    frame = int(row["frame"])
    view = int(row["view_id"])
    img_p = Path(row["input_path"])

    print("\n" + "=" * 80)
    print("case:", case, "seq:", seq, "frame:", frame, "view:", view)
    print("image:", img_p)

    if seq not in data["data_dict"]:
        print("[MISS seq]", seq)
        continue

    seq_data = data["data_dict"][seq]
    img = Image.open(img_p).convert("RGB")
    draw = ImageDraw.Draw(img)
    W, H = img.size

    bbox = seq_data["bbox"][frame, view].astype(np.float32)
    center = bbox[:2]
    scale = float(bbox[2])

    groups = {
        "right": ("red", seq_data["2d"]["joints.right"][frame, view]),
        "left": ("lime", seq_data["2d"]["joints.left"][frame, view]),
        "object_kp": ("cyan", seq_data["2d"]["kp3d"][frame, view]),
        "object_bbox": ("yellow", seq_data["2d"]["bbox3d"][frame, view]),
    }

    inside_report = {}

    converted = {}
    for name, (color, pts_orig) in groups.items():
        pts_crop = official_to_crop(pts_orig, center, scale)
        converted[name] = pts_crop
        inside_report[name] = f"{count_inside(pts_crop, W, H)}/{len(pts_crop)}"
        draw_points(draw, pts_crop, color)

    # Draw object bbox edges.
    b = converted["object_bbox"]
    edges = [
        (0,1),(1,2),(2,3),(3,0),
        (4,5),(5,6),(6,7),(7,4),
        (0,4),(1,5),(2,6),(3,7),
    ]
    if len(b) >= 8:
        for i, j in edges:
            x1, y1 = b[i]
            x2, y2 = b[j]
            draw.line((x1, y1, x2, y2), fill="yellow", width=2)

    title = f"{case}: red=right green=left cyan=obj yellow=bbox"
    draw.text((20, 20), title, fill="white")

    out_p = OUT_DIR / f"{case}_gt_2d_official_overlay.jpg"
    img.save(out_p)

    print("bbox:", bbox)
    print("inside:", inside_report)
    print("[OK] wrote", out_p)

    summary.append({
        "case": case,
        "seq": seq,
        "frame": frame,
        "view": view,
        "bbox": bbox.tolist(),
        **inside_report,
        "overlay_path": str(out_p),
    })

summary_p = OUT_DIR / "overlay_inside_summary.csv"
pd.DataFrame(summary).to_csv(summary_p, index=False)
print("\n[OK] wrote summary:", summary_p)
