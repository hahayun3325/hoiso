from pathlib import Path
import json
import math
import numpy as np
import trimesh
from scipy.spatial import cKDTree

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT_ROOT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit"
MANIFEST = FIT_ROOT / "metrics/standalone_fitter_input_manifest.json"

OUT_VIS = FIT_ROOT / "visuals"
OUT_METRICS = FIT_ROOT / "metrics"
OUT_OUT = FIT_ROOT / "outputs"
OUT_VIS.mkdir(parents=True, exist_ok=True)
OUT_METRICS.mkdir(parents=True, exist_ok=True)
OUT_OUT.mkdir(parents=True, exist_ok=True)

def load_mesh(path):
    obj = trimesh.load(path, force=None, process=False)
    if isinstance(obj, trimesh.Scene):
        geoms = [g for g in obj.geometry.values() if hasattr(g, "vertices") and len(g.vertices) > 0]
        return trimesh.util.concatenate(geoms)
    return obj

def colorize(mesh, rgba):
    m = mesh.copy()
    m.visual.vertex_colors = rgba
    return m

def sample(mesh, n=8000, seed=0):
    rng = np.random.default_rng(seed)
    if len(mesh.faces) > 0:
        pts, _ = trimesh.sample.sample_surface(mesh, min(n, max(n, len(mesh.faces))))
        return pts
    v = np.asarray(mesh.vertices)
    if len(v) <= n:
        return v
    return v[rng.choice(len(v), size=n, replace=False)]

def pca_axis(points):
    c = points.mean(axis=0)
    X = points - c
    _, _, vt = np.linalg.svd(X, full_matrices=False)
    return c, vt

def rotation_about_axis(point, axis, angle_rad):
    axis = axis / max(np.linalg.norm(axis), 1e-12)
    x, y, z = axis
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    C = 1.0 - c

    R = np.array([
        [c + x*x*C,   x*y*C - z*s, x*z*C + y*s],
        [y*x*C + z*s, c + y*y*C,   y*z*C - x*s],
        [z*x*C - y*s, z*y*C + x*s, c + z*z*C],
    ], dtype=np.float64)

    T1 = np.eye(4)
    T1[:3, 3] = -point

    T2 = np.eye(4)
    T2[:3, :3] = R

    T3 = np.eye(4)
    T3[:3, 3] = point

    return T3 @ T2 @ T1

def estimate_hinge_axis(base, screen):
    b = sample(base, 12000, seed=10)
    s = sample(screen, 12000, seed=11)

    tree = cKDTree(b)
    d, idx = tree.query(s, k=1)

    keep = d <= np.percentile(d, 5)
    if keep.sum() < 30:
        keep = d <= np.percentile(d, 10)

    mids = 0.5 * (s[keep] + b[idx[keep]])
    center, axes = pca_axis(mids)

    axis = axes[0]
    axis = axis / max(np.linalg.norm(axis), 1e-12)

    return {
        "center": center,
        "axis": axis,
        "num_pairs": int(keep.sum()),
        "mean_pair_distance": float(d[keep].mean()),
        "p95_pair_distance": float(np.percentile(d[keep], 95)),
    }

def physical_score(base, screen):
    b = sample(base, 10000, seed=20)
    s = sample(screen, 10000, seed=21)

    tree = cKDTree(b)
    d, _ = tree.query(s, k=1)

    # Good: a small hinge neighborhood close to base.
    # Bad: too much of screen extremely close to base, suggesting overlap.
    hinge_gap_p1 = float(np.percentile(d, 1))
    hinge_gap_p5 = float(np.percentile(d, 5))
    near_2mm = float((d < 0.002).mean())
    near_5mm = float((d < 0.005).mean())

    # Base-plane crossing proxy.
    center, axes = pca_axis(b)
    normal = axes[-1]
    signed = (s - center) @ normal
    smaller_side_ratio = float(min((signed > 0).mean(), (signed < 0).mean()))

    score = (
        1.0 * abs(hinge_gap_p5 - 0.010)
        + 0.5 * max(0.0, near_5mm - 0.25)
        + 0.5 * max(0.0, smaller_side_ratio - 0.30)
    )

    return {
        "score": float(score),
        "hinge_gap_p1": hinge_gap_p1,
        "hinge_gap_p5": hinge_gap_p5,
        "near_fraction_2mm": near_2mm,
        "near_fraction_5mm": near_5mm,
        "screen_base_plane_smaller_side_ratio": smaller_side_ratio,
    }

data = json.loads(MANIFEST.read_text())
paths = {k: Path(v["path"]) for k, v in data["paths"].items() if v["exists"]}

screen0 = load_mesh(paths["screen_part"])
base = load_mesh(paths["keyboard_base_part"])
hinge = load_mesh(paths["hinge_part"])

hinge_info = estimate_hinge_axis(base, screen0)

# Conservative local search only. Do not move base. Do not rescale.
angles = np.arange(-20, 20.0001, 2.0)

candidates = []
for a in angles:
    T = rotation_about_axis(
        hinge_info["center"],
        hinge_info["axis"],
        math.radians(float(a)),
    )
    screen = screen0.copy()
    screen.apply_transform(T)

    phys = physical_score(base, screen)

    # Prefer small changes unless they clearly improve physical score.
    total_score = phys["score"] + 0.0005 * abs(float(a))

    candidates.append({
        "angle_deg": float(a),
        "score": float(total_score),
        "physical": phys,
        "screen": screen,
    })

best = sorted(candidates, key=lambda x: x["score"])[0]

best_screen = best["screen"]
union = trimesh.util.concatenate([base, best_screen, hinge])

base.export(OUT_OUT / "keyboard_base_v0_1_fixed.ply")
best_screen.export(OUT_OUT / "screen_v0_1_hinge_adjusted.ply")
hinge.export(OUT_OUT / "hinge_v0_1_fixed.ply")
union.export(OUT_OUT / "object_v0_1_conservative_union.ply")

scene = trimesh.Scene()
scene.add_geometry(colorize(best_screen, [0, 0, 255, 160]), node_name="screen_v0_1_blue")
scene.add_geometry(colorize(base, [255, 140, 0, 200]), node_name="keyboard_base_fixed_orange")
scene.add_geometry(colorize(hinge, [255, 0, 255, 220]), node_name="hinge_fixed_magenta")

if "guidance_obj" in paths:
    scene.add_geometry(colorize(load_mesh(paths["guidance_obj"]), [180, 180, 180, 70]), node_name="current_guidance_obj_gray")
if "guidance_hand" in paths:
    scene.add_geometry(colorize(load_mesh(paths["guidance_hand"]), [0, 255, 0, 120]), node_name="current_guidance_hand_green")

out_glb = OUT_VIS / "standalone_fitter_v0_1_conservative_scene.glb"
scene.export(out_glb)

report = {
    "case_id": "alapuse01",
    "stage": "standalone_fast_articulated_fitter_v0_1_conservative",
    "decision_scope": "conservative hinge-only optimization in current FollowMyHold frame",
    "important_constraints": [
        "keyboard_base root pose fixed",
        "shared scale fixed",
        "screen rotates only around estimated hinge axis",
        "no independent screen translation",
        "no full FollowMyHold code edit"
    ],
    "hinge_axis": {
        "center": hinge_info["center"].tolist(),
        "axis": hinge_info["axis"].tolist(),
        "num_pairs": hinge_info["num_pairs"],
        "mean_pair_distance": hinge_info["mean_pair_distance"],
        "p95_pair_distance": hinge_info["p95_pair_distance"]
    },
    "angle_search": {
        "min": float(angles.min()),
        "max": float(angles.max()),
        "step": 2.0,
        "num_candidates": len(angles)
    },
    "best": {
        "angle_deg": best["angle_deg"],
        "score": best["score"],
        "physical": best["physical"]
    },
    "top_candidates": [
        {
            "angle_deg": c["angle_deg"],
            "score": c["score"],
            "physical": c["physical"]
        }
        for c in sorted(candidates, key=lambda x: x["score"])[:10]
    ],
    "outputs": {
        "scene": str(out_glb),
        "union": str(OUT_OUT / "object_v0_1_conservative_union.ply")
    }
}

out_json = OUT_METRICS / "standalone_fitter_v0_1_conservative_metrics.json"
out_json.write_text(json.dumps(report, indent=2))

print("[OK] wrote", out_glb)
print("[OK] wrote", out_json)
print("[best_angle_deg]", best["angle_deg"])
print("[best_score]", best["score"])
print("[best_physical]", json.dumps(best["physical"], indent=2))
