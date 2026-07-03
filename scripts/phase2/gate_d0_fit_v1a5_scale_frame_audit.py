from pathlib import Path
import json
import numpy as np
import trimesh
from PIL import Image
from scipy.spatial import cKDTree

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit_v1_getting_unstuck"
V1A5 = FIT / "scale_frame_audit_v1a5"

SEL_RUN = Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse01_selector_v41_refined_pipeline")
ACTIVE = CASE_ROOT / "integrated_gates/gate_a_part_repair/active_clean_parts"

VIS = V1A5 / "visuals"
MET = V1A5 / "metrics"
OUT = V1A5 / "outputs"
for p in [VIS, MET, OUT]:
    p.mkdir(parents=True, exist_ok=True)

MAN = FIT / "inputs/fit_input_manifest.json"

paths = {
    "hand_E_aligned_mano": SEL_RUN / "aligned_mano/alapuse01_hamer_aligned_mano.ply",
    "screen_active": ACTIVE / "screen.ply",
    "base_active": ACTIVE / "keyboard_base.ply",
    "hinge_active": ACTIVE / "hinge.ply",
    "manifest": MAN
}

def resolve(p):
    p = Path(p)
    if p.exists():
        return p
    if not p.is_absolute():
        for root in [FIT, CASE_ROOT]:
            q = root / p
            if q.exists():
                return q
    return p

def load_mesh(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    obj = trimesh.load(path, force=None, process=False)
    if isinstance(obj, trimesh.Scene):
        geoms = [g for g in obj.geometry.values() if hasattr(g, "vertices") and len(g.vertices) > 0]
        if not geoms:
            raise ValueError(f"empty scene: {path}")
        return trimesh.util.concatenate(geoms)
    return obj

def colorize(mesh, rgba):
    m = mesh.copy()
    m.visual.vertex_colors = rgba
    return m

def bbox_info(mesh):
    b = np.asarray(mesh.bounds, dtype=float)
    ext = b[1] - b[0]
    return {
        "bbox_min": b[0].tolist(),
        "bbox_max": b[1].tolist(),
        "extent_xyz": ext.tolist(),
        "max_extent": float(ext.max()),
        "xy_max_extent": float(ext[:2].max()),
        "center": mesh.centroid.tolist(),
        "num_vertices": int(len(mesh.vertices)),
        "num_faces": int(len(mesh.faces))
    }

def sample(mesh, n=8000, seed=0):
    rng = np.random.default_rng(seed)
    if len(mesh.faces) > 0:
        pts, _ = trimesh.sample.sample_surface(mesh, n)
        return pts
    v = np.asarray(mesh.vertices)
    if len(v) <= n:
        return v
    return v[rng.choice(len(v), n, replace=False)]

def nearest_stats(A, B):
    if len(A) == 0 or len(B) == 0:
        return None
    tree = cKDTree(B)
    d, idx = tree.query(A, k=1)
    return {
        "min": float(np.min(d)),
        "p1": float(np.percentile(d, 1)),
        "p5": float(np.percentile(d, 5)),
        "p10": float(np.percentile(d, 10)),
        "mean": float(np.mean(d)),
        "within_02": int((d < 0.02).sum()),
        "within_05": int((d < 0.05).sum())
    }

def backproject_mask(mask_path, depth, K, max_points=12000, seed=0):
    mask = np.asarray(Image.open(mask_path).convert("L"))
    H, W = depth.shape[:2]
    if mask.shape[:2] != (H, W):
        mask = np.asarray(Image.fromarray(mask).resize((W, H), Image.NEAREST))
    valid = (mask > 127) & np.isfinite(depth) & (depth > 0) & (depth < 20)

    ys, xs = np.where(valid)
    if len(xs) == 0:
        return np.zeros((0, 3), dtype=np.float32)

    z = depth[ys, xs].astype(np.float32)

    # Robustly trim depth outliers.
    lo, hi = np.percentile(z, [2, 98])
    keep = (z >= lo) & (z <= hi)
    xs, ys, z = xs[keep], ys[keep], z[keep]

    pts = np.stack([
        (xs - K[0, 2]) * z / K[0, 0],
        (ys - K[1, 2]) * z / K[1, 1],
        z
    ], axis=1).astype(np.float32)

    if len(pts) > max_points:
        rng = np.random.default_rng(seed)
        pts = pts[rng.choice(len(pts), max_points, replace=False)]
    return pts

def point_bbox_info(pts):
    if len(pts) == 0:
        return {"exists": False}
    b0 = pts.min(axis=0)
    b1 = pts.max(axis=0)
    ext = b1 - b0
    return {
        "exists": True,
        "bbox_min": b0.tolist(),
        "bbox_max": b1.tolist(),
        "extent_xyz": ext.tolist(),
        "max_extent": float(ext.max()),
        "xy_max_extent": float(ext[:2].max()),
        "center": pts.mean(axis=0).tolist(),
        "num_points": int(len(pts))
    }

def scale_mesh_about(mesh, center, scale):
    out = mesh.copy()
    v = np.asarray(out.vertices)
    out.vertices = (v - center) * scale + center
    return out

def translate_mesh(mesh, vec):
    out = mesh.copy()
    out.apply_translation(vec)
    return out

def export_scene(name, hand, screen, base, hinge):
    scene = trimesh.Scene()
    scene.add_geometry(colorize(hand, [0, 255, 0, 120]), node_name="hand_green")
    scene.add_geometry(colorize(screen, [0, 190, 255, 150]), node_name="screen_lid_cyan")
    scene.add_geometry(colorize(base, [255, 0, 255, 140]), node_name="base_magenta")
    scene.add_geometry(colorize(hinge, [255, 180, 0, 180]), node_name="hinge_yellow")
    out = VIS / f"{name}.glb"
    scene.export(out)
    return str(out)

# Load meshes
hand = load_mesh(paths["hand_E_aligned_mano"])
screen = load_mesh(paths["screen_active"])
base = load_mesh(paths["base_active"])
hinge = load_mesh(paths["hinge_active"])
obj = trimesh.util.concatenate([screen, base, hinge])

# Load image/depth evidence
m = json.loads(MAN.read_text())
K = np.asarray(m["camera"]["K"], dtype=np.float32)
depth = np.load(resolve(m["depth_metric_npy"])).astype(np.float32)
depth[~np.isfinite(depth)] = np.nan

lid_pts = backproject_mask(resolve(m["mask_lid"]), depth, K, seed=1)
base_pts = backproject_mask(resolve(m["mask_base"]), depth, K, seed=2)
obj_depth_pts = np.concatenate([lid_pts, base_pts], axis=0) if len(lid_pts) + len(base_pts) else np.zeros((0,3), dtype=np.float32)

# Scale estimates
mesh_info = {
    "hand": bbox_info(hand),
    "screen": bbox_info(screen),
    "base": bbox_info(base),
    "hinge": bbox_info(hinge),
    "active_object_combined": bbox_info(obj)
}
depth_info = {
    "lid_mask_depth_cloud": point_bbox_info(lid_pts),
    "base_mask_depth_cloud": point_bbox_info(base_pts),
    "object_mask_depth_cloud": point_bbox_info(obj_depth_pts)
}

active_xy = mesh_info["active_object_combined"]["xy_max_extent"]
target_xy = depth_info["object_mask_depth_cloud"].get("xy_max_extent", None)

if target_xy and active_xy > 1e-8:
    object_scale_to_depth_xy = float(np.clip(target_xy / active_xy, 0.1, 10.0))
else:
    object_scale_to_depth_xy = None

hand_to_active_object_xy_ratio = float(mesh_info["hand"]["xy_max_extent"] / max(active_xy, 1e-9))
hand_to_active_object_max_ratio = float(mesh_info["hand"]["max_extent"] / max(mesh_info["active_object_combined"]["max_extent"], 1e-9))

# Contact diagnostics before/after object scale
hand_pts = np.asarray(hand.vertices)
screen_pts = sample(screen, 10000, seed=3)
original_contact = nearest_stats(hand_pts, screen_pts)

scenes = {
    "E_original_scale_audit": export_scene("E_original_scale_audit", hand, screen, base, hinge)
}

scaled_report = None
if object_scale_to_depth_xy is not None:
    c = np.asarray(obj.centroid)
    screen_s = scale_mesh_about(screen, c, object_scale_to_depth_xy)
    base_s = scale_mesh_about(base, c, object_scale_to_depth_xy)
    hinge_s = scale_mesh_about(hinge, c, object_scale_to_depth_xy)

    scaled_screen_pts = sample(screen_s, 10000, seed=4)
    scaled_contact = nearest_stats(hand_pts, scaled_screen_pts)

    # Compute a diagnostic snap after scaling.
    d_tree = cKDTree(scaled_screen_pts)
    d, idx = d_tree.query(hand_pts, k=1)
    k = max(20, min(80, int(0.10 * len(hand_pts))))
    ids = np.argsort(d)[:k]
    hand_patch = hand_pts[ids]
    screen_patch = scaled_screen_pts[idx[ids]]
    snap_vec = hand_patch.mean(axis=0) - screen_patch.mean(axis=0)
    snap_norm = float(np.linalg.norm(snap_vec))

    screen_ss = translate_mesh(screen_s, snap_vec)
    base_ss = translate_mesh(base_s, snap_vec)
    hinge_ss = translate_mesh(hinge_s, snap_vec)

    scaled_scene = export_scene("E_object_scaled_to_moge_mask_xy", hand, screen_s, base_s, hinge_s)
    scaled_snap_scene = export_scene("E_object_scaled_then_snap_debug", hand, screen_ss, base_ss, hinge_ss)

    scaled_report = {
        "object_scale_to_depth_xy": object_scale_to_depth_xy,
        "scaled_contact_hand_to_screen": scaled_contact,
        "scaled_snap_vector": snap_vec.tolist(),
        "scaled_snap_norm_m": snap_norm,
        "scenes": {
            "object_scaled_to_moge_mask_xy": scaled_scene,
            "object_scaled_then_snap_debug": scaled_snap_scene
        }
    }
    scenes.update(scaled_report["scenes"])

# Decision
flags = []
if object_scale_to_depth_xy is None:
    decision = "FAIL_NO_DEPTH_SCALE_ESTIMATE"
elif object_scale_to_depth_xy > 1.35:
    flags.append("ACTIVE_OBJECT_LIKELY_UNDER_SCALED_RELATIVE_TO_MOGE_MASK_DEPTH")
    decision = "SCALE_MISMATCH_OBJECT_UNDER_SCALED"
elif object_scale_to_depth_xy < 0.75:
    flags.append("ACTIVE_OBJECT_LIKELY_OVER_SCALED_RELATIVE_TO_MOGE_MASK_DEPTH")
    decision = "SCALE_MISMATCH_OBJECT_OVER_SCALED"
else:
    decision = "OBJECT_SCALE_ROUGHLY_MATCHES_MOGE_MASK_DEPTH"

if hand_to_active_object_xy_ratio > 0.70:
    flags.append("HAND_LARGE_RELATIVE_TO_ACTIVE_OBJECT_XY")

if scaled_report is not None and scaled_report["scaled_snap_norm_m"] > 0.10:
    flags.append("LARGE_ROOT_TRANSLATION_STILL_REQUIRED_AFTER_OBJECT_SCALE")

report = {
    "case_id": "alapuse01",
    "stage": "Gate D-0 fit v1a5 scale-frame audit",
    "uses_gt": False,
    "inputs": {k: str(v) for k, v in paths.items()},
    "mesh_bbox_info": mesh_info,
    "depth_bbox_info": depth_info,
    "ratios": {
        "object_scale_to_depth_xy": object_scale_to_depth_xy,
        "hand_to_active_object_xy_ratio": hand_to_active_object_xy_ratio,
        "hand_to_active_object_max_ratio": hand_to_active_object_max_ratio
    },
    "original_contact_hand_to_screen": original_contact,
    "scaled_object_report": scaled_report,
    "flags": flags,
    "decision": decision,
    "scenes": scenes,
    "decision_rule": {
        "object_under_scaled": "object_scale_to_depth_xy > 1.35",
        "object_over_scaled": "object_scale_to_depth_xy < 0.75",
        "hand_large_relative_to_object": "hand_to_active_object_xy_ratio > 0.70",
        "still_frame_issue": "scaled_snap_norm_m > 0.10 after object scale correction"
    },
    "next_step": "inspect scale audit scenes, then decide object-scale correction vs transform-chain debugging"
}

out = MET / "fit_v1a5_scale_frame_audit.json"
out.write_text(json.dumps(report, indent=2))

print("[OK] wrote", out)
print("[decision]", decision)
print("[flags]", flags)
print("[object_scale_to_depth_xy]", object_scale_to_depth_xy)
print("[hand_to_active_object_xy_ratio]", hand_to_active_object_xy_ratio)
if scaled_report:
    print("[scaled_snap_norm_m]", scaled_report["scaled_snap_norm_m"])
for k, v in scenes.items():
    print(k, "->", v)
