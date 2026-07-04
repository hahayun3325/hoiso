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
V02 = AKET / "gate_d_sandbox_v0_2_signed_collision_audit"

VIS = V02 / "visuals"
MET = V02 / "metrics"
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

def sample_vertices(mesh, n=20000, seed=0):
    v = np.asarray(mesh.vertices)
    if len(v) <= n:
        return v, np.arange(len(v))
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(v), n, replace=False)
    return v[idx], idx

def make_sphere(center, radius, rgba):
    s = trimesh.creation.icosphere(subdivisions=2, radius=radius)
    s.apply_translation(np.asarray(center))
    s.visual.vertex_colors = rgba
    return s

def dist_stats(d):
    return {
        "min": float(np.min(d)),
        "p1": float(np.percentile(d, 1)),
        "p5": float(np.percentile(d, 5)),
        "p10": float(np.percentile(d, 10)),
        "mean": float(np.mean(d)),
        "within_003": int((d < 0.003).sum()),
        "within_005": int((d < 0.005).sum()),
        "within_01": int((d < 0.01).sum()),
        "within_02": int((d < 0.02).sum()),
        "within_05": int((d < 0.05).sum())
    }

def signed_distance_igl(points, mesh):
    """
    Try libigl signed distance. Negative values are usually inside.
    This can still be noisy when the object mesh is open/non-watertight.
    """
    import igl
    V = np.asarray(mesh.vertices, dtype=np.float64)
    F = np.asarray(mesh.faces, dtype=np.int32)
    P = np.asarray(points, dtype=np.float64)
    out = igl.signed_distance(P, V, F)
    if isinstance(out, tuple):
        return np.asarray(out[0], dtype=np.float64)
    return np.asarray(out, dtype=np.float64)

def signed_distance_trimesh(points, mesh):
    """
    Fallback. May require rtree. Sign can be unreliable for non-watertight meshes.
    """
    pq = trimesh.proximity.ProximityQuery(mesh)
    return np.asarray(pq.signed_distance(points), dtype=np.float64)

hand_path = SEL_RUN / "guidance_out/aket01_hand.ply"
obj_path = SEL_RUN / "guidance_out/aket01_obj.ply"
body_path = ACTIVE / "body.ply"

hand = load_mesh(hand_path)
body = load_mesh(body_path)
obj = load_mesh(obj_path)

hand_pts, hand_idx = sample_vertices(hand, n=20000, seed=10)
body_pts, _ = sample_vertices(body, n=20000, seed=11)

# Unsigned distance proxy, same family as v0/v0.1.
tree = cKDTree(body_pts)
d_unsigned, nn = tree.query(hand_pts, k=1)

method = None
signed = None
signed_error = None
try:
    signed = signed_distance_igl(hand_pts, body)
    method = "igl.signed_distance"
except Exception as e1:
    try:
        signed = signed_distance_trimesh(hand_pts, body)
        method = "trimesh.proximity.signed_distance"
    except Exception as e2:
        signed_error = f"igl failed: {repr(e1)} | trimesh failed: {repr(e2)}"

report = {
    "case_id": "aket01",
    "stage": "Gate D sandbox v0.2 signed collision audit",
    "hand_path": str(hand_path),
    "body_path": str(body_path),
    "object_path": str(obj_path),
    "unsigned_hand_to_body": dist_stats(d_unsigned),
    "signed_distance_method": method,
    "signed_distance_error": signed_error,
    "mesh_quality_warning": "Signed distance can be unreliable if the body mesh is open or non-watertight."
}

scene = trimesh.Scene()
scene.add_geometry(colorize(obj, [255, 255, 255, 35]), node_name="guidance_object_white")
scene.add_geometry(colorize(body, [0, 180, 255, 145]), node_name="body_blue")
scene.add_geometry(colorize(hand, [0, 255, 0, 120]), node_name="hand_green")

decision = "VISUAL_REVIEW_REQUIRED"

if signed is not None:
    negative = signed < -0.002
    shallow_negative = (signed < 0.0) & (signed >= -0.002)
    deep_negative = signed < -0.005

    report["signed_distance"] = {
        "min": float(np.min(signed)),
        "p1": float(np.percentile(signed, 1)),
        "p5": float(np.percentile(signed, 5)),
        "mean": float(np.mean(signed)),
        "negative_count_lt_0": int((signed < 0).sum()),
        "negative_count_lt_minus_002": int(negative.sum()),
        "negative_count_lt_minus_005": int(deep_negative.sum()),
        "negative_ratio_lt_minus_002": float(negative.mean()),
        "negative_ratio_lt_minus_005": float(deep_negative.mean())
    }

    # Visualize strongest suspected penetration points.
    idx = np.argsort(signed)[:80]
    for p, s in zip(hand_pts[idx], signed[idx]):
        if s < -0.005:
            scene.add_geometry(make_sphere(p, 0.005, [255, 0, 0, 255]), node_name="deep_negative_red")
        elif s < -0.002:
            scene.add_geometry(make_sphere(p, 0.004, [255, 120, 0, 230]), node_name="negative_orange")
        elif s < 0:
            scene.add_geometry(make_sphere(p, 0.003, [255, 255, 0, 200]), node_name="shallow_negative_yellow")

    deep = int(deep_negative.sum())
    moderate = int(negative.sum())

    if deep == 0 and moderate < 30:
        decision = "PASS_SIGNED_COLLISION_AUDIT_LOW_RISK"
    elif deep == 0:
        decision = "PASS_WITH_SHALLOW_COLLISION_WARNING"
    else:
        decision = "FAIL_SIGNED_COLLISION_DEEP_INTERSECTION"
else:
    # No signed distance available; fall back to proxy decision only.
    if report["unsigned_hand_to_body"]["within_003"] <= 5:
        decision = "PARTIAL_PASS_UNSIGNED_PROXY_ONLY"
    else:
        decision = "WARNING_UNSIGNED_PROXY_CLOSE_POINTS"

visual_path = VIS / "aket01_gate_d_sandbox_v0_2_signed_collision_audit.glb"
scene.export(visual_path)

report["decision"] = decision
report["visual"] = str(visual_path)
report["interpretation"] = [
    "This is a collision audit, not an optimizer.",
    "Green = hand, blue = verified body.",
    "Red/orange/yellow markers indicate suspected signed-distance penetration when signed distance is available.",
    "If signed distance fails, use the unsigned result only as a proxy and do not claim physical collision pass."
]

report_path = MET / "aket01_gate_d_sandbox_v0_2_signed_collision_report.json"
report_path.write_text(json.dumps(report, indent=2))

print("[OK] visual:", visual_path)
print("[OK] report:", report_path)
print("[decision]", decision)
print(json.dumps(report, indent=2)[:4000])
