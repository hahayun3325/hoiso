from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit_v1_getting_unstuck"
V1B0 = FIT / "v1b0_corrected_hand_root_seed"
V1B1 = FIT / "v1b1_lid_targeted_residual_correction"

VIS = V1B1 / "visuals"
MET = V1B1 / "metrics"
OUT = V1B1 / "outputs"
for p in [VIS, MET, OUT]:
    p.mkdir(parents=True, exist_ok=True)

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

def translate(mesh, vec):
    m = mesh.copy()
    m.apply_translation(np.asarray(vec, dtype=float))
    return m

def sample(mesh, n=12000, seed=0):
    rng = np.random.default_rng(seed)
    if len(mesh.faces) > 0:
        pts, _ = trimesh.sample.sample_surface(mesh, n)
        return pts
    v = np.asarray(mesh.vertices)
    if len(v) <= n:
        return v
    return v[rng.choice(len(v), n, replace=False)]

def stats_to_surface(points, surface_pts):
    tree = cKDTree(surface_pts)
    d, idx = tree.query(points, k=1)
    return d, idx, {
        "min": float(np.min(d)),
        "p1": float(np.percentile(d, 1)),
        "p5": float(np.percentile(d, 5)),
        "p10": float(np.percentile(d, 10)),
        "mean": float(np.mean(d)),
        "within_02": int(np.sum(d < 0.02)),
        "within_05": int(np.sum(d < 0.05))
    }

def make_spheres(points, radius=0.006, rgba=(255, 0, 0, 255), max_points=80):
    pts = np.asarray(points)
    if len(pts) > max_points:
        pts = pts[np.linspace(0, len(pts)-1, max_points).astype(int)]
    geoms = []
    for p in pts:
        s = trimesh.creation.uv_sphere(radius=radius)
        s.apply_translation(p)
        s.visual.vertex_colors = rgba
        geoms.append(s)
    return geoms

def export_scene(name, hand, screen, base, hinge, markers=None):
    scene = trimesh.Scene()
    scene.add_geometry(colorize(hand, [0, 255, 0, 140]), node_name="hand_green")
    scene.add_geometry(colorize(screen, [0, 190, 255, 145]), node_name="screen_active_cyan")
    scene.add_geometry(colorize(base, [255, 0, 255, 145]), node_name="base_active_magenta")
    scene.add_geometry(colorize(hinge, [255, 180, 0, 180]), node_name="hinge_yellow")
    if markers:
        for i, g in enumerate(markers):
            scene.add_geometry(g, node_name=f"marker_{i:03d}")
    out = VIS / f"{name}.glb"
    scene.export(out)
    return str(out)

# Load v1b0 seed.
hand = load_mesh(V1B0 / "outputs/hand_v1b0_scaled_aligned_mano_guidance_root.ply")
screen = load_mesh(V1B0 / "outputs/screen_v1b0_object_scaled.ply")
base = load_mesh(V1B0 / "outputs/base_v1b0_object_scaled.ply")
hinge = load_mesh(V1B0 / "outputs/hinge_v1b0_object_scaled.ply")

# Load semantic relabels from image evidence.
lid_files = sorted(FIT.rglob("lid_relabel_v1.ply"))
base_files = sorted(FIT.rglob("base_relabel_v1.ply"))
if not lid_files or not base_files:
    raise FileNotFoundError("Need lid_relabel_v1.ply and base_relabel_v1.ply before v1b1.")

lid_sem = load_mesh(lid_files[0])
base_sem = load_mesh(base_files[0])

hand_v = np.asarray(hand.vertices)
lid_pts = sample(lid_sem, 16000, seed=1)
base_pts = sample(base_sem, 16000, seed=2)

# Identify current patches.
d_lid, idx_lid, lid_stats0 = stats_to_surface(hand_v, lid_pts)
d_base, idx_base, base_stats0 = stats_to_surface(hand_v, base_pts)

k = min(80, max(30, int(0.03 * len(hand_v))))
lid_patch_ids = np.argsort(d_lid)[:k]
base_patch_ids = np.argsort(d_base)[:k]

lid_patch = hand_v[lid_patch_ids]
base_patch = hand_v[base_patch_ids]

# Direction: move the hand patch nearest semantic lid toward its nearest lid surface.
nearest_lid_pts = lid_pts[idx_lid[lid_patch_ids]]
raw_vec = nearest_lid_pts.mean(axis=0) - lid_patch.mean(axis=0)
raw_norm = float(np.linalg.norm(raw_vec))
unit = raw_vec / (raw_norm + 1e-12)

# Candidate translations.
candidates = {
    "no_move": np.zeros(3),
    "full_lid_patch_snap_debug": raw_vec,
}

for cm in [2, 4, 6, 8, 10, 12]:
    dist = cm / 100.0
    candidates[f"clipped_{cm:02d}cm_lid_direction"] = unit * min(dist, raw_norm)

# Small grid around the lid direction. This is still diagnostic, not full optimization.
side = np.linspace(-0.04, 0.04, 5)
grid_id = 0
for a in np.linspace(0.0, min(0.12, raw_norm), 7):
    center = unit * a
    # Add small local offsets in x/y/z.
    for dx in side:
        for dy in side:
            for dz in [-0.02, 0.0, 0.02]:
                candidates[f"grid_{grid_id:04d}"] = center + np.array([dx, dy, dz])
                grid_id += 1

def evaluate(vec):
    h = translate(hand, vec)
    hv = np.asarray(h.vertices)
    d_l, _, st_l = stats_to_surface(hv, lid_pts)
    d_b, _, st_b = stats_to_surface(hv, base_pts)

    # Use closest-to-lid patch and closest-to-base patch from original hand for stable comparison.
    lid_patch_now = hv[lid_patch_ids]
    base_patch_now = hv[base_patch_ids]
    _, _, st_lid_patch_to_lid = stats_to_surface(lid_patch_now, lid_pts)
    _, _, st_base_patch_to_base = stats_to_surface(base_patch_now, base_pts)

    # Low score is better.
    # Want lid patch close, base patch not too close, and movement small.
    base_penalty = max(0.0, 0.04 - st_base_patch_to_base["mean"])
    score = (
        st_lid_patch_to_lid["mean"]
        + 2.0 * base_penalty
        + 0.25 * float(np.linalg.norm(vec))
    )

    return h, {
        "translation": vec.tolist(),
        "translation_norm": float(np.linalg.norm(vec)),
        "all_hand_to_lid": st_l,
        "all_hand_to_base": st_b,
        "lid_patch_to_lid": st_lid_patch_to_lid,
        "base_patch_to_base": st_base_patch_to_base,
        "score_lower_better": float(score)
    }

results = {}
for name, vec in candidates.items():
    h, r = evaluate(vec)
    results[name] = r

# Pick best scored candidate, but visual decision still required.
ranked = sorted(results.items(), key=lambda kv: kv[1]["score_lower_better"])
top_names = [ranked[0][0], "no_move", "full_lid_patch_snap_debug",
             "clipped_04cm_lid_direction", "clipped_08cm_lid_direction", "clipped_12cm_lid_direction"]
top_names = list(dict.fromkeys([n for n in top_names if n in candidates]))

visuals = {}
for name in top_names:
    h, _ = evaluate(candidates[name])
    hv = np.asarray(h.vertices)
    # Blue = lid patch, red = base patch.
    markers = []
    markers += make_spheres(hv[lid_patch_ids], radius=0.006, rgba=(0, 0, 255, 255), max_points=80)
    markers += make_spheres(hv[base_patch_ids], radius=0.006, rgba=(255, 0, 0, 255), max_points=80)
    visuals[name] = export_scene(f"v1b1_{name}", h, screen, base, hinge, markers)

# Save best candidate mesh.
best_name = ranked[0][0]
best_hand, _ = evaluate(candidates[best_name])
best_hand.export(OUT / "hand_v1b1_best_lid_targeted_residual.ply")
screen.export(OUT / "screen_v1b1_object_scaled.ply")
base.export(OUT / "base_v1b1_object_scaled.ply")
hinge.export(OUT / "hinge_v1b1_object_scaled.ply")

decision = "VISUAL_CHECK_REQUIRED"
best = results[best_name]
if best["translation_norm"] > 0.12:
    decision = "FAIL_RESIDUAL_TOO_LARGE"
elif best["lid_patch_to_lid"]["within_05"] > 20 and best["base_patch_to_base"]["within_05"] < 20:
    decision = "NUMERIC_PASS_VISUAL_CHECK_REQUIRED"
elif best["base_patch_to_base"]["within_05"] >= best["lid_patch_to_lid"]["within_05"]:
    decision = "LIKELY_FAIL_BASE_CONTACT_REMAINS"
else:
    decision = "PARTIAL_VISUAL_CHECK_REQUIRED"

report = {
    "case_id": "alapuse01",
    "stage": "Gate D-0 fit v1b1 lid-targeted residual correction",
    "uses_gt": False,
    "input_seed": "v1b0 corrected hand-root seed",
    "semantic_lid": str(lid_files[0]),
    "semantic_base": str(base_files[0]),
    "initial": {
        "hand_to_lid_semantic": lid_stats0,
        "hand_to_base_semantic": base_stats0
    },
    "raw_lid_patch_snap_vec": raw_vec.tolist(),
    "raw_lid_patch_snap_norm": raw_norm,
    "ranked_top10": [
        {"name": n, **r} for n, r in ranked[:10]
    ],
    "visuals": visuals,
    "outputs": {
        "best_hand": str(OUT / "hand_v1b1_best_lid_targeted_residual.ply"),
        "screen": str(OUT / "screen_v1b1_object_scaled.ply"),
        "base": str(OUT / "base_v1b1_object_scaled.ply"),
        "hinge": str(OUT / "hinge_v1b1_object_scaled.ply")
    },
    "decision": decision,
    "decision_rule": {
        "accept": "small residual produces visual lid/screen contact and avoids base/keyboard contact",
        "partial": "lid gets closer but base contact remains or residual is still large",
        "fail": "needs large residual or still contacts base"
    },
    "next_step": "inspect v1b1 scenes before any full optimizer"
}

out = MET / "fit_v1b1_lid_targeted_residual_correction.json"
out.write_text(json.dumps(report, indent=2))

print("[OK] wrote", out)
print("[decision]", decision)
print("[raw_lid_patch_snap_norm]", raw_norm)
print("[best]", best_name)
print(json.dumps(best, indent=2))
print("[visuals]")
for k, v in visuals.items():
    print(k, "->", v)
