from pathlib import Path
import sys
import numpy as np

ARCTIC_ROOT = Path("/home/fredcui/Projects/arctic")
sys.path.insert(0, str(ARCTIC_ROOT))

from common.data_utils import transform

SPLIT = Path("/home/fredcui/Projects/arctic/unpack/arctic_data/data/splits/p1_train.npy")

SEQ = "s01/ketchup_grab_01"
FRAME = 147
VIEW = 7
RES = [1000, 1000]

data = np.load(SPLIT, allow_pickle=True).item()
seq = data["data_dict"][SEQ]

bbox = seq["bbox"][FRAME, VIEW].astype(np.float32)
center = bbox[:2]
scale = float(bbox[2])

crop_side = scale * 200.0
top_left = center - crop_side / 2.0

def manual(points):
    points = np.asarray(points, dtype=np.float32)
    return (points - top_left[None, :]) * (1000.0 / crop_side)

def official(points):
    return np.asarray([transform(p, center, scale, RES, invert=0, rot=0) for p in points], dtype=np.float32)

groups = {
    "right": seq["2d"]["joints.right"][FRAME, VIEW],
    "left": seq["2d"]["joints.left"][FRAME, VIEW],
    "object_kp": seq["2d"]["kp3d"][FRAME, VIEW],
    "object_bbox": seq["2d"]["bbox3d"][FRAME, VIEW],
}

for name, pts in groups.items():
    m = manual(pts)
    o = official(pts)
    d = np.linalg.norm(m - o, axis=1)
    print(name)
    print("  mean px diff:", float(d.mean()))
    print("  max  px diff:", float(d.max()))
