from pathlib import Path
import pickle
import numpy as np
from PIL import Image

OAK = Path(__import__("os").environ["OAKINK_DIR"]).resolve()
IMG = OAK / "image/stream_release_v2/A01023_0001_0002/2021-10-12-17-13-00/south_east_color_90.png"
ROOT = Path.home() / "foho_phase0/inspection/oakink_000/gt_assets/oakink_image_annotation/frame90/anno"
SEQ = "A01023_0001_0002__2021-10-12-17-13-00__0__90"

# rough hand/object area in image, chosen from visual observation
# You can adjust if needed.
ROUGH_BBOX = np.array([320, 120, 520, 300], dtype=float)  # x1,y1,x2,y2

def load_pkl(p):
    with open(p, "rb") as f:
        return pickle.load(f)

def project(points, K):
    pts = np.asarray(points, dtype=np.float64)
    z = pts[:,2]
    good = z > 1e-6
    pts = pts[good]
    z = z[good]
    u = K[0,0] * pts[:,0] / z + K[0,2]
    v = K[1,1] * pts[:,1] / z + K[1,2]
    return np.stack([u, v], axis=1)

W, H = Image.open(IMG).size
print("image size:", W, H)
print("rough bbox:", ROUGH_BBOX.tolist())

for vid in range(4):
    suffix = f"{SEQ}__{vid}.pkl"
    hand_v = np.asarray(load_pkl(ROOT / "hand_v" / suffix))
    hand_j = np.asarray(load_pkl(ROOT / "hand_j" / suffix))
    K = np.asarray(load_pkl(ROOT / "cam_intr" / suffix), dtype=np.float64)

    pts = project(hand_v, K)
    pts = pts[(pts[:,0] >= 0) & (pts[:,0] < W) & (pts[:,1] >= 0) & (pts[:,1] < H)]

    if len(pts) == 0:
        print("view_id", vid, "no projected pts")
        continue

    bbox = np.array([pts[:,0].min(), pts[:,1].min(), pts[:,0].max(), pts[:,1].max()])
    cxcy = np.array([(bbox[0]+bbox[2])/2, (bbox[1]+bbox[3])/2])
    rcxcy = np.array([(ROUGH_BBOX[0]+ROUGH_BBOX[2])/2, (ROUGH_BBOX[1]+ROUGH_BBOX[3])/2])
    center_dist = np.linalg.norm(cxcy - rcxcy)

    inside = (
        (pts[:,0] >= ROUGH_BBOX[0]) & (pts[:,0] <= ROUGH_BBOX[2]) &
        (pts[:,1] >= ROUGH_BBOX[1]) & (pts[:,1] <= ROUGH_BBOX[3])
    ).mean()

    print(f"view_id={vid} bbox={bbox.tolist()} center_dist={center_dist:.2f} inside_rough_bbox={inside:.3f}")
