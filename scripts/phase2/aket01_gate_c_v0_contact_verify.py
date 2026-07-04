from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

DATA = Path("/home/fredcui/foho_phase0")
CASE_ROOT = DATA / "phase2_gateA_part_recon/cases/aket01"
AKET = CASE_ROOT / "integrated_gates/positive_control_aket01"
ACTIVE = AKET / "active_parts_v0"
SEL_RUN = DATA / "phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_aket01_selector_v41_refined_pipeline"
GATEC = AKET / "gate_c_v0_contact_verification"

VIS = GATEC / "visuals"
MET = GATEC / "metrics"
VIS.mkdir(parents=True, exist_ok=True)
MET.mkdir(parents=True, exist_ok=True)

def load_mesh(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    obj = trimesh.load(path, process=False)
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

def sample_vertices(mesh, n=10000, seed=0):
    v = np.asarray(mesh.vertices)
    if len(v) <= n:
        return v, np.arange(len(v))
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(v), n, replace=False)
    return v[idx], idx

def dist_report(hand, part, seed=0):
    hv, hidx = sample_vertices(hand, 10000, seed=seed)
    pv, pidx = sample_vertices(part, 10000, seed=seed + 100)
    tree = cKDTree(pv)
    d, nn = tree.query(hv, k=1)

    nearest_part_points = pv[nn]
    order = np.argsort(d)

    return {
        "min": float(d.min()),
        "p1": float(np.percentile(d, 1)),
        "p5": float(np.percentile(d, 5)),
        "p10": float(np.percentile(d, 10)),
        "mean": float(d.mean()),
        "within_005": int((d < 0.005).sum()),
        "within_01": int((d < 0.01).sum()),
        "within_02": int((d < 0.02).sum()),
        "within_05": int((d < 0.05).sum()),
        "nearest_hand_points": hv[order[:40]].tolist(),
        "nearest_part_points": nearest_part_points[order[:40]].tolist()
    }

def make_sphere(center, radius, rgba):
    s = trimesh.creation.icosphere(subdivisions=2, radius=radius)
    s.apply_translation(center)
    s.visual.vertex_colors = rgba
    return s

hand_path = SEL_RUN / "guidance_out/aket01_hand.ply"
obj_path = SEL_RUN / "guidance_out/aket01_obj.ply"

hand = load_mesh(hand_path)
obj = load_mesh(obj_path)

part_paths = {
    p.stem: p for p in sorted(ACTIVE.glob("*.ply"))
}

parts = {name: load_mesh(path) for name, path in part_paths.items()}

reports = {}
for i, (name, mesh) in enumerate(parts.items()):
    reports[name] = dist_report(hand, mesh, seed=i)

# Simple scoring: prefer many close points, then lower p5.
scores = {}
for name, r in reports.items():
    scores[name] = (
        2.0 * r["within_01"]
        + 1.0 * r["within_02"]
        + 0.25 * r["within_05"]
        - 100.0 * r["p5"]
    )

best_part = max(scores, key=scores.get) if scores else None

scene = trimesh.Scene()
scene.add_geometry(colorize(hand, [0, 255, 0, 145]), node_name="guidance_hand_green")
scene.add_geometry(colorize(obj, [255, 255, 255, 45]), node_name="guidance_object_white")

colors = {
    "body": [0, 180, 255, 145],
    "top_or_cap": [255, 0, 255, 145],
    "cap": [255, 0, 255, 145],
    "neck": [255, 180, 0, 165],
    "residual_uncertain": [255, 180, 0, 100],
}
for name, mesh in parts.items():
    scene.add_geometry(colorize(mesh, colors.get(name, [0, 0, 255, 120])), node_name=f"part_{name}")

# Mark nearest points for each part. Red = hand-side contact candidates, blue = object-part-side candidates.
for name, r in reports.items():
    if name == best_part:
        hand_rgba = [255, 0, 0, 255]
        part_rgba = [0, 0, 255, 255]
        radius = 0.006
    else:
        hand_rgba = [255, 120, 0, 180]
        part_rgba = [80, 80, 255, 180]
        radius = 0.004

    for pt in r["nearest_hand_points"][:20]:
        scene.add_geometry(make_sphere(np.array(pt), radius, hand_rgba), node_name=f"marker_hand_to_{name}")
    for pt in r["nearest_part_points"][:20]:
        scene.add_geometry(make_sphere(np.array(pt), radius, part_rgba), node_name=f"marker_part_{name}")

visual_path = VIS / "aket01_gate_c_v0_contact_markers.glb"
scene.export(visual_path)

decision = "VISUAL_REVIEW_REQUIRED"
if best_part == "body" and reports["body"]["p5"] < 0.02 and reports["body"]["within_02"] > 50:
    decision = "PASS_BODY_CONTACT_CANDIDATE"
elif best_part:
    decision = f"CHECK_BEST_PART_{best_part.upper()}"

report = {
    "case_id": "aket01",
    "stage": "Gate C v0 contact verification",
    "hand_path": str(hand_path),
    "object_path": str(obj_path),
    "part_paths": {k: str(v) for k, v in part_paths.items()},
    "reports": reports,
    "scores": scores,
    "best_part": best_part,
    "decision": decision,
    "visual": str(visual_path),
    "interpretation": [
        "Red markers are nearest hand-side contact candidates.",
        "Blue markers are nearest object-part-side contact candidates.",
        "For aket01, expected primary contact is body, not residual_uncertain.",
        "If markers fall on visible grasp fingers and bottle body, proceed to contact scorer sandbox."
    ]
}

report_path = MET / "aket01_gate_c_v0_contact_report.json"
report_path.write_text(json.dumps(report, indent=2))

print("[OK] visual:", visual_path)
print("[OK] report:", report_path)
print("[best_part]", best_part)
print("[decision]", decision)
print(json.dumps({k: {kk: reports[k][kk] for kk in ["min", "p5", "p10", "mean", "within_01", "within_02", "within_05"]} for k in reports}, indent=2))
