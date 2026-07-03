from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit_v1_getting_unstuck"
MAN = FIT / "inputs/fit_input_manifest.json"

m = json.loads(MAN.read_text())

OUT = FIT / "metrics"
VIS = FIT / "visuals"
OUT.mkdir(parents=True, exist_ok=True)
VIS.mkdir(parents=True, exist_ok=True)

def resolve(p):
    p = Path(p)
    return p if p.is_absolute() else CASE_ROOT / p

def load_mesh(path):
    obj = trimesh.load(path, force="mesh", process=False)
    if isinstance(obj, trimesh.Scene):
        geoms = [g for g in obj.geometry.values() if hasattr(g, "vertices") and len(g.vertices) > 0]
        return trimesh.util.concatenate(geoms)
    return obj

def transform_vertices(v, name):
    v = np.asarray(v, dtype=np.float32)
    if name == "identity_xyz":
        return v
    if name == "flip_y":
        return np.stack([v[:,0], -v[:,1], v[:,2]], axis=1)
    if name == "flip_z":
        return np.stack([v[:,0], v[:,1], -v[:,2]], axis=1)
    if name == "flip_yz":
        return np.stack([v[:,0], -v[:,1], -v[:,2]], axis=1)
    raise ValueError(name)

def apply_transform(mesh, name):
    out = mesh.copy()
    out.vertices = transform_vertices(np.asarray(out.vertices), name)
    return out

def colorize(mesh, rgba):
    m = mesh.copy()
    m.visual.vertex_colors = rgba
    return m

def marker(center, radius, rgba):
    s = trimesh.creation.icosphere(subdivisions=2, radius=radius)
    s.apply_translation(center)
    s.visual.vertex_colors = rgba
    return s

def dist_stats(A, B):
    tree = cKDTree(np.asarray(B.vertices))
    d, _ = tree.query(np.asarray(A.vertices), k=1)
    return {
        "min": float(np.min(d)),
        "p1": float(np.percentile(d, 1)),
        "p5": float(np.percentile(d, 5)),
        "p10": float(np.percentile(d, 10)),
        "mean": float(np.mean(d)),
        "within_5mm": int((d <= 0.005).sum()),
        "within_10mm": int((d <= 0.010).sum()),
        "within_20mm": int((d <= 0.020).sum())
    }

lid_fit = load_mesh(FIT / "outputs/lid_fitted_v1.ply")
base_fit = load_mesh(FIT / "outputs/base_fitted_v1.ply")
lid_relabel = load_mesh(FIT / "outputs/lid_relabel_v1.ply")
base_relabel = load_mesh(FIT / "outputs/base_relabel_v1.ply")
hand_raw = load_mesh(resolve(m["hand_mesh"]))

candidates = ["identity_xyz", "flip_y", "flip_z", "flip_yz"]
report = {}

for t in candidates:
    hand = apply_transform(hand_raw, t)

    h2lid = dist_stats(hand, lid_fit)
    h2base = dist_stats(hand, base_fit)

    # prefer hand close to lid but not too close to base
    score = (
        h2lid["p5"]
        + 0.5 * h2lid["mean"]
        - 0.2 * min(h2base["p5"], 0.05)
    )

    report[t] = {
        "hand_to_fitted_lid": h2lid,
        "hand_to_fitted_base": h2base,
        "score_lower_better": float(score)
    }

ranking = sorted(
    [{"transform": k, **v} for k, v in report.items()],
    key=lambda r: r["score_lower_better"]
)

best = ranking[0]["transform"]

# Export a scene with the best hand transform.
scene = trimesh.Scene()
scene.add_geometry(colorize(lid_fit, [0, 220, 220, 170]), node_name="lid_fitted_v1_cyan")
scene.add_geometry(colorize(base_fit, [255, 0, 255, 150]), node_name="base_fitted_v1_magenta")
scene.add_geometry(colorize(apply_transform(hand_raw, best), [0, 255, 0, 120]), node_name=f"hand_best_{best}_green")

# Add all candidate hands lightly for debugging.
for t in candidates:
    if t == best:
        continue
    scene.add_geometry(colorize(apply_transform(hand_raw, t), [120, 120, 120, 50]), node_name=f"hand_candidate_{t}_gray")

scene_path = VIS / "fit_v1a_hand_frame_diagnostic_scene.glb"
scene.export(scene_path)

out = {
    "case_id": "alapuse01",
    "stage": "Gate D-0 fit v1a hand-frame diagnostic",
    "best_transform_by_distance": best,
    "ranking": ranking,
    "decision_rule": {
        "good": "best hand transform visually places fingers near lid/screen and not under base",
        "bad": "all hand transforms are far/wrong, meaning hand/object alignment requires a saved FMH transform rather than simple axis flip"
    },
    "scene": str(scene_path)
}

out_path = OUT / "fit_v1a_hand_frame_diagnostic.json"
out_path.write_text(json.dumps(out, indent=2))

print("[OK] wrote", out_path)
print("[OK] wrote", scene_path)
print(json.dumps(out, indent=2))
