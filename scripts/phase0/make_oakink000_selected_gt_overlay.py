from pathlib import Path
from PIL import Image, ImageDraw
import pickle
import numpy as np
import trimesh

SEL = Path.home() / "foho_phase0/inspection/oakink_000/gt_assets/oakink_image_annotation/selected_south_east_frame90"
GT_OBJ = Path.home() / "foho_phase0/inspection/oakink_000/gt_assets/A01023.obj"

OUT = Path.home() / "foho_phase0/inspection/oakink_000/oakink000_selected_gt_overlay.jpg"

def load_pkl(name):
    with open(SEL / name, "rb") as f:
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

def draw_points(img, pts2d, color, radius=2, max_points=2000):
    d = ImageDraw.Draw(img)
    pts = np.asarray(pts2d)
    if len(pts) > max_points:
        idx = np.linspace(0, len(pts)-1, max_points).astype(int)
        pts = pts[idx]
    for x, y in pts:
        if 0 <= x < img.width and 0 <= y < img.height:
            d.ellipse([x-radius, y-radius, x+radius, y+radius], fill=color)

img = Image.open(SEL / "image.png").convert("RGB")
K = np.asarray(load_pkl("cam_intr.pkl"), dtype=np.float64)
hand_v = np.asarray(load_pkl("hand_v.pkl"), dtype=np.float64)
hand_j = np.asarray(load_pkl("hand_j.pkl"), dtype=np.float64)
T_obj = np.asarray(load_pkl("obj_transf.pkl"), dtype=np.float64)

# hand overlay: red vertices, green joints
draw_points(img, project(hand_v, K), color=(255, 0, 0), radius=1, max_points=1000)
draw_points(img, project(hand_j, K), color=(0, 255, 0), radius=4, max_points=21)

# object overlay: blue sampled object vertices after object transform
if GT_OBJ.exists():
    mesh = trimesh.load(GT_OBJ, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

    verts = np.asarray(mesh.vertices, dtype=np.float64)
    if len(verts) > 5000:
        idx = np.linspace(0, len(verts)-1, 5000).astype(int)
        verts = verts[idx]

    verts_h = np.concatenate([verts, np.ones((len(verts), 1))], axis=1)
    verts_cam = (T_obj @ verts_h.T).T[:, :3]

    draw_points(img, project(verts_cam, K), color=(0, 80, 255), radius=1, max_points=3000)
else:
    print("[WARN] missing GT object:", GT_OBJ)

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT, quality=95)
print("[OK] wrote", OUT)
