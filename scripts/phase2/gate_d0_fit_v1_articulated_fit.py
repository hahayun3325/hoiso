from pathlib import Path
import json
import math
import numpy as np
import torch
import trimesh
from PIL import Image

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit_v1_getting_unstuck"
MAN = FIT / "inputs/fit_input_manifest.json"
PROBE = FIT / "metrics/projection_frame_probe.json"

m = json.loads(MAN.read_text())
probe = json.loads(PROBE.read_text()) if PROBE.exists() else {}
transform_name = probe.get("recommended_transform", "flip_yz")

device = "cuda" if torch.cuda.is_available() else "cpu"
print("[device]", device)
print("[projection_transform]", transform_name)

def resolve(p):
    p = Path(p)
    return p if p.is_absolute() else CASE_ROOT / p

def np_transform(v, name):
    v = np.asarray(v, dtype=np.float32)
    if name == "identity_xyz":
        return v
    if name == "flip_y":
        return np.stack([v[:,0], -v[:,1], v[:,2]], axis=1)
    if name == "flip_z":
        return np.stack([v[:,0], v[:,1], -v[:,2]], axis=1)
    if name == "flip_yz":
        return np.stack([v[:,0], -v[:,1], -v[:,2]], axis=1)
    raise ValueError(f"Unsupported transform for fitter v1: {name}")

def load_mesh(path):
    obj = trimesh.load(path, force="mesh", process=False)
    if isinstance(obj, trimesh.Scene):
        geoms = [g for g in obj.geometry.values() if hasattr(g, "vertices") and len(g.vertices) > 0]
        return trimesh.util.concatenate(geoms)
    return obj

def colorize(mesh, rgba):
    m = mesh.copy()
    m.visual.vertex_colors = rgba
    return m

def sample_mesh(mesh, n=2500, seed=0):
    if len(mesh.faces) == 0:
        pts = np.asarray(mesh.vertices)
    else:
        pts, _ = trimesh.sample.sample_surface(mesh, n)
    pts = np_transform(pts, transform_name)
    return torch.tensor(pts, dtype=torch.float32, device=device)

def mesh_to_camera_frame(mesh):
    out = mesh.copy()
    out.vertices = np_transform(np.asarray(out.vertices), transform_name)
    return out

def backproject(mask_path, depth, K, n=2500, seed=0):
    mask = np.asarray(Image.open(mask_path).convert("L")) > 127
    valid = mask & np.isfinite(depth) & (depth > 0) & (depth < 20)

    ys, xs = np.where(valid)
    if len(xs) == 0:
        raise ValueError(f"No valid depth pixels under mask: {mask_path}")

    z = depth[ys, xs].astype(np.float32)

    # Remove extreme depth outliers.
    lo, hi = np.percentile(z, [2, 98])
    keep = (z >= lo) & (z <= hi)
    xs, ys, z = xs[keep], ys[keep], z[keep]

    pts = np.stack([
        (xs - K[0, 2]) * z / K[0, 0],
        (ys - K[1, 2]) * z / K[1, 1],
        z
    ], axis=1).astype(np.float32)

    if len(pts) > n:
        rng = np.random.default_rng(seed)
        pts = pts[rng.choice(len(pts), size=n, replace=False)]

    return torch.tensor(pts, dtype=torch.float32, device=device)

def chamfer(a, b):
    d = torch.cdist(a, b)
    return d.min(dim=1).values.mean() + d.min(dim=0).values.mean()

def rot_from_axis_angle(w):
    theta = torch.linalg.norm(w) + 1e-8
    k = w / theta
    kx = torch.stack([
        torch.stack([torch.tensor(0., device=device), -k[2], k[1]]),
        torch.stack([k[2], torch.tensor(0., device=device), -k[0]]),
        torch.stack([-k[1], k[0], torch.tensor(0., device=device)])
    ])
    I = torch.eye(3, device=device)
    return I + torch.sin(theta) * kx + (1 - torch.cos(theta)) * (kx @ kx)

def rotate_about_axis(points, pivot, axis, angle):
    R = rot_from_axis_angle(axis * angle)
    return (points - pivot) @ R.T + pivot

# Inputs
K = np.asarray(m["camera"]["K"], dtype=np.float32)
depth = np.load(resolve(m["depth_metric_npy"])).astype(np.float32)
depth[~np.isfinite(depth)] = np.nan

lid_mesh = load_mesh(FIT / "outputs/lid_relabel_v1.ply")
base_mesh = load_mesh(FIT / "outputs/base_relabel_v1.ply")
hand_mesh = load_mesh(resolve(m["hand_mesh"]))

target_lid = backproject(resolve(m["mask_lid"]), depth, K, n=2500, seed=1)
target_base = backproject(resolve(m["mask_base"]), depth, K, n=2500, seed=2)

lid_pts = sample_mesh(lid_mesh, n=2500, seed=3)
base_pts = sample_mesh(base_mesh, n=2500, seed=4)

hand_cam = mesh_to_camera_frame(hand_mesh)
hand_pts_all = torch.tensor(np.asarray(hand_cam.vertices), dtype=torch.float32, device=device)

# Contact prior: use closest hand vertices to the initial lid as a stable local patch.
with torch.no_grad():
    d0 = torch.cdist(hand_pts_all, lid_pts).min(dim=1).values
    k = max(20, int(0.01 * len(hand_pts_all)))
    contact_ids = torch.argsort(d0)[:k]
    contact_hand_pts = hand_pts_all[contact_ids]

# Hinge estimate from closest lid/base sampled points.
with torch.no_grad():
    d_lb = torch.cdist(lid_pts, base_pts)
    nearest_lid_ids = torch.argsort(d_lb.min(dim=1).values)[:250]
    seam = lid_pts[nearest_lid_ids]
    pivot0 = seam.mean(dim=0)
    _, _, vh = torch.linalg.svd(seam - pivot0)
    axis0 = vh[0]
    axis0 = axis0 / torch.clamp(torch.linalg.norm(axis0), min=1e-8)

# Initialize pose/scale from base target.
base_extent = torch.clamp(base_pts.max(dim=0).values - base_pts.min(dim=0).values, min=1e-6)
tgt_extent = torch.clamp(target_base.max(dim=0).values - target_base.min(dim=0).values, min=1e-6)
init_scale = torch.clamp(tgt_extent[:2].max() / base_extent[:2].max(), min=0.2, max=5.0)

log_s = torch.tensor([float(torch.log(init_scale).item())], device=device, requires_grad=True)
rot_w = torch.zeros(3, dtype=torch.float32, device=device, requires_grad=True)
trans = (target_base.mean(dim=0) - base_pts.mean(dim=0)).detach().clone().requires_grad_(True)
theta = torch.tensor([math.radians(25.0)], dtype=torch.float32, device=device, requires_grad=True)

def apply_model(base_local, lid_local):
    s = torch.exp(log_s)
    R = rot_from_axis_angle(rot_w)

    lid_h = rotate_about_axis(lid_local, pivot0, axis0, theta[0])
    base_w = (s * base_local) @ R.T + trans
    lid_w = (s * lid_h) @ R.T + trans

    seam_h = rotate_about_axis(seam, pivot0, axis0, theta[0])
    seam_w = (s * seam_h) @ R.T + trans

    return base_w, lid_w, seam_w

optimizer = torch.optim.Adam([log_s, rot_w, trans, theta], lr=0.01)

history = []
for it in range(150):
    optimizer.zero_grad()
    base_w, lid_w, seam_w = apply_model(base_pts, lid_pts)

    loss_base = chamfer(base_w, target_base)
    loss_lid = chamfer(lid_w, target_lid)

    contact_d = torch.cdist(contact_hand_pts, lid_w).min(dim=1).values
    loss_contact = contact_d.mean()

    seam_to_base = torch.cdist(seam_w, base_w).min(dim=1).values
    loss_hinge = torch.clamp(seam_to_base - 0.015, min=0).mean()

    # Keep laptop angle plausible.
    theta_low = math.radians(5)
    theta_high = math.radians(75)
    loss_theta_limit = torch.clamp(theta_low - theta[0], min=0) ** 2 + torch.clamp(theta[0] - theta_high, min=0) ** 2

    # Mild regularizers to avoid wild pose changes.
    loss_pose_reg = 0.01 * torch.linalg.norm(rot_w) + 0.001 * torch.linalg.norm(trans)

    loss = (
        1.0 * loss_base +
        1.0 * loss_lid +
        0.35 * loss_contact +
        1.0 * loss_hinge +
        1.0 * loss_theta_limit +
        loss_pose_reg
    )

    loss.backward()
    optimizer.step()

    if it % 25 == 0 or it == 149:
        row = {
            "iter": it,
            "loss": float(loss.detach().cpu()),
            "base": float(loss_base.detach().cpu()),
            "lid": float(loss_lid.detach().cpu()),
            "contact": float(loss_contact.detach().cpu()),
            "hinge": float(loss_hinge.detach().cpu()),
            "theta_deg": float(math.degrees(theta.detach().cpu().item())),
            "scale": float(torch.exp(log_s).detach().cpu().item())
        }
        history.append(row)
        print(row)

# Export fitted meshes in camera/fit frame.
with torch.no_grad():
    s = float(torch.exp(log_s).detach().cpu().item())
    R = rot_from_axis_angle(rot_w).detach().cpu().numpy()
    t = trans.detach().cpu().numpy()
    theta_final = float(theta.detach().cpu().item())
    axis_np = axis0.detach().cpu().numpy()
    pivot_np = pivot0.detach().cpu().numpy()

def rotate_np(v, pivot, axis, angle):
    axis = axis / max(np.linalg.norm(axis), 1e-12)
    x, y, z = axis
    c = math.cos(angle)
    ss = math.sin(angle)
    C = 1 - c
    Raxis = np.array([
        [c + x*x*C, x*y*C - z*ss, x*z*C + y*ss],
        [y*x*C + z*ss, c + y*y*C, y*z*C - x*ss],
        [z*x*C - y*ss, z*y*C + x*ss, c + z*z*C]
    ], dtype=np.float32)
    return (v - pivot) @ Raxis.T + pivot

base_out = mesh_to_camera_frame(base_mesh)
lid_out = mesh_to_camera_frame(lid_mesh)

base_v = np.asarray(base_out.vertices, dtype=np.float32)
lid_v = np.asarray(lid_out.vertices, dtype=np.float32)
lid_v = rotate_np(lid_v, pivot_np, axis_np, theta_final)

base_out.vertices = (s * base_v) @ R.T + t
lid_out.vertices = (s * lid_v) @ R.T + t

FIT.joinpath("outputs").mkdir(parents=True, exist_ok=True)
FIT.joinpath("visuals").mkdir(parents=True, exist_ok=True)
FIT.joinpath("metrics").mkdir(parents=True, exist_ok=True)

base_out.export(FIT / "outputs/base_fitted_v1.ply")
lid_out.export(FIT / "outputs/lid_fitted_v1.ply")

# Metrics
lid_sample, _ = trimesh.sample.sample_surface(lid_out, 2500)
lid_sample_t = torch.tensor(lid_sample, dtype=torch.float32, device=device)
contact_final = torch.cdist(contact_hand_pts, lid_sample_t).min(dim=1).values

metrics = {
    "case_id": "alapuse01",
    "stage": "Gate D-0 image-evidence articulated fitting v1",
    "projection_transform": transform_name,
    "theta_deg": float(math.degrees(theta_final)),
    "scale": float(s),
    "contact_patch_to_lid_m": {
        "min": float(contact_final.min().detach().cpu()),
        "mean": float(contact_final.mean().detach().cpu()),
        "max": float(contact_final.max().detach().cpu())
    },
    "history": history,
    "decision_rule": {
        "PASS": "visual plausible laptop; lid moves toward hand; contact mean < 0.015m",
        "PARTIAL": "visual improved but contact mean 0.015-0.040m",
        "FAIL": "object collapses, lid far from hand, or severe inter-part crossing"
    }
}

(FIT / "metrics/fit_v1_metrics.json").write_text(json.dumps(metrics, indent=2))

scene = trimesh.Scene()
scene.add_geometry(colorize(lid_out, [0, 220, 220, 170]), node_name="lid_fitted_v1_cyan")
scene.add_geometry(colorize(base_out, [255, 0, 255, 170]), node_name="base_fitted_v1_magenta")
scene.add_geometry(colorize(hand_cam, [0, 255, 0, 110]), node_name="hand_camera_frame_green")

scene_path = FIT / "visuals/fit_v1_scene.glb"
scene.export(scene_path)

print("[OK] wrote", scene_path)
print("[OK] wrote", FIT / "metrics/fit_v1_metrics.json")
print(json.dumps(metrics, indent=2)[:3000])
