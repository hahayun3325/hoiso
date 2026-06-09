from pathlib import Path
from PIL import Image, ImageDraw
import pickle
import numpy as np
import trimesh

HOME = Path.home()

GT_DIR = HOME / "foho_phase0/inspection/oakink_000/gt_assets/oakink_image_annotation/selected_south_east_frame90"
GT_OBJ_PATH = HOME / "foho_phase0/inspection/oakink_000/gt_assets/A01023.obj"

RUNS = {
    "baseline": "oakink000_default_short",
    "gpt55_selector": "oakink000_gpt55_short_selector_auto_frag_v7_truefile",
}

OUT = HOME / "foho_phase0/inspection/oakink_000/oakink000_paper_like_metric_overlay.jpg"

def load_pkl(path):
    with open(path, "rb") as f:
        return pickle.load(f)

def load_mesh(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh

def find_pred_meshes(run_dir):
    obj_candidates = [run_dir / "guidance_out/oakink_obj.ply", run_dir / "guidance_out/test_obj.ply"]
    hand_candidates = [run_dir / "guidance_out/oakink_hand.ply", run_dir / "guidance_out/test_hand.ply"]
    obj = next((p for p in obj_candidates if p.exists()), None)
    hand = next((p for p in hand_candidates if p.exists()), None)
    return hand, obj

def project(points, K):
    pts = np.asarray(points, dtype=np.float64)
    z = pts[:, 2]
    good = z > 1e-6
    pts = pts[good]
    z = z[good]
    u = K[0,0] * pts[:,0] / z + K[0,2]
    v = K[1,1] * pts[:,1] / z + K[1,2]
    return np.stack([u, v], axis=1)

def draw_points(img, pts2d, color, radius=1, max_points=3000):
    d = ImageDraw.Draw(img)
    pts = np.asarray(pts2d)
    if len(pts) > max_points:
        idx = np.linspace(0, len(pts)-1, max_points).astype(int)
        pts = pts[idx]
    for x, y in pts:
        if 0 <= x < img.width and 0 <= y < img.height:
            d.ellipse([x-radius, y-radius, x+radius, y+radius], fill=color)

def transform_points(points, s, R, t):
    return s * (points @ R.T) + t

def umeyama(src, dst):
    src = np.asarray(src, dtype=np.float64)
    dst = np.asarray(dst, dtype=np.float64)
    mu_src = src.mean(axis=0)
    mu_dst = dst.mean(axis=0)
    X = src - mu_src
    Y = dst - mu_dst
    cov = (Y.T @ X) / len(src)
    U, D, Vt = np.linalg.svd(cov)
    S = np.eye(3)
    if np.linalg.det(U @ Vt) < 0:
        S[-1, -1] = -1
    R = U @ S @ Vt
    var_src = (X ** 2).sum() / len(src)
    s = np.trace(np.diag(D) @ S) / max(var_src, 1e-12)
    t = mu_dst - s * (R @ mu_src)
    return float(s), R, t

def sample_mesh_vertices(mesh, n=5000):
    verts = np.asarray(mesh.vertices, dtype=np.float64)
    if len(verts) > n:
        idx = np.linspace(0, len(verts)-1, n).astype(int)
        verts = verts[idx]
    return verts

K = np.asarray(load_pkl(GT_DIR / "cam_intr.pkl"), dtype=np.float64)
gt_hand_v = np.asarray(load_pkl(GT_DIR / "hand_v.pkl"), dtype=np.float64)
T_obj = np.asarray(load_pkl(GT_DIR / "obj_transf.pkl"), dtype=np.float64)

img_base = Image.open(GT_DIR / "image.png").convert("RGB")

# GT object in camera
gt_obj = load_mesh(GT_OBJ_PATH)
gt_v = sample_mesh_vertices(gt_obj, 5000)
gt_vh = np.concatenate([gt_v, np.ones((len(gt_v), 1))], axis=1)
gt_vcam = (T_obj @ gt_vh.T).T[:, :3]

cards = []

# GT card
gt_img = img_base.copy()
draw_points(gt_img, project(gt_hand_v, K), (255, 0, 0), radius=1, max_points=1000)
draw_points(gt_img, project(gt_vcam, K), (0, 80, 255), radius=1, max_points=2500)
cards.append(("GT overlay", gt_img))

for label, run_id in RUNS.items():
    run = HOME / "foho_phase0/runs" / run_id
    hand_path, obj_path = find_pred_meshes(run)
    card = img_base.copy()

    if hand_path and obj_path:
        pred_hand = load_mesh(hand_path)
        pred_obj = load_mesh(obj_path)

        pred_hand_v = np.asarray(pred_hand.vertices, dtype=np.float64)
        s, R, t = umeyama(pred_hand_v, gt_hand_v)

        obj_v = sample_mesh_vertices(pred_obj, 5000)
        obj_aligned = transform_points(obj_v, s, R, t)

        draw_points(card, project(gt_hand_v, K), (255, 0, 0), radius=1, max_points=800)
        draw_points(card, project(obj_aligned, K), (255, 180, 0), radius=1, max_points=3000)
    else:
        ImageDraw.Draw(card).text((20, 20), "MISSING PRED", fill=(255, 0, 0))

    cards.append((label, card))

CELL_W, CELL_H = 420, 300
canvas = Image.new("RGB", (CELL_W * len(cards), CELL_H), (235, 235, 235))
draw = ImageDraw.Draw(canvas)

for i, (title, img) in enumerate(cards):
    x = i * CELL_W
    draw.text((x + 10, 10), title, fill=(0, 0, 0))
    img.thumbnail((CELL_W - 20, CELL_H - 45))
    canvas.paste(img, (x + 10, 40))

OUT.parent.mkdir(parents=True, exist_ok=True)
canvas.save(OUT, quality=95)
print("[OK] wrote", OUT)
