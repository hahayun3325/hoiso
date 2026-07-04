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
V02A = AKET / "gate_d_sandbox_v0_2a_sdf_sanity_audit"

VIS = V02A / "visuals"
MET = V02A / "metrics"
VIS.mkdir(parents=True, exist_ok=True)
MET.mkdir(parents=True, exist_ok=True)

def load_mesh(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    obj = trimesh.load(path, process=False)
    if isinstance(obj, trimesh.Scene):
        geoms = [g for g in obj.geometry.values() if hasattr(g, "vertices") and len(g.vertices) > 0]
        return trimesh.util.concatenate(geoms)
    return obj

def safe_float(x):
    try:
        return float(x)
    except Exception:
        return None

def colorize(mesh, rgba):
    m = mesh.copy()
    m.visual.vertex_colors = rgba
    return m

def make_sphere(center, radius, rgba):
    s = trimesh.creation.icosphere(subdivisions=2, radius=radius)
    s.apply_translation(np.asarray(center))
    s.visual.vertex_colors = rgba
    return s

def signed_distance(points, mesh):
    import igl
    V = np.asarray(mesh.vertices, dtype=np.float64)
    F = np.asarray(mesh.faces, dtype=np.int32)
    P = np.asarray(points, dtype=np.float64)
    out = igl.signed_distance(P, V, F)
    if isinstance(out, tuple):
        return np.asarray(out[0], dtype=np.float64)
    return np.asarray(out, dtype=np.float64)

hand_path = SEL_RUN / "guidance_out/aket01_hand.ply"
obj_path = SEL_RUN / "guidance_out/aket01_obj.ply"
body_path = ACTIVE / "body.ply"

hand = load_mesh(hand_path)
obj = load_mesh(obj_path)
body = load_mesh(body_path)

body_vertices = np.asarray(body.vertices)
body_faces = np.asarray(body.faces)
hand_vertices = np.asarray(hand.vertices)

# Mesh quality diagnostics.
components = body.split(only_watertight=False)
component_sizes = [int(len(c.vertices)) for c in components]

bbox_min, bbox_max = body.bounds
bbox_center = body.bounding_box.centroid
bbox_extents = body.bounding_box.extents
bbox_diag = float(np.linalg.norm(bbox_extents))

# Probe points:
# center should often be inside if mesh is closed;
# far outside points should be outside.
probe_points = []
probe_names = []

probe_points.append(bbox_center)
probe_names.append("bbox_center")

for axis in range(3):
    for sign in [-1, 1]:
        p = bbox_center.copy()
        p[axis] += sign * bbox_diag
        probe_points.append(p)
        probe_names.append(f"outside_axis{axis}_{sign:+d}")

probe_points = np.asarray(probe_points, dtype=np.float64)

signed_report = {}
signed_error = None
try:
    sd_probe = signed_distance(probe_points, body)
    signed_report["probe_points"] = [
        {
            "name": name,
            "point": p.tolist(),
            "signed_distance": float(s)
        }
        for name, p, s in zip(probe_names, probe_points, sd_probe)
    ]

    # Recompute hand signed distance on all hand vertices.
    sd_hand = signed_distance(hand_vertices, body)
    signed_report["hand_signed_distance"] = {
        "min": float(np.min(sd_hand)),
        "p1": float(np.percentile(sd_hand, 1)),
        "p5": float(np.percentile(sd_hand, 5)),
        "mean": float(np.mean(sd_hand)),
        "negative_count_lt_0": int((sd_hand < 0).sum()),
        "negative_count_lt_minus_002": int((sd_hand < -0.002).sum()),
        "negative_count_lt_minus_005": int((sd_hand < -0.005).sum()),
        "total_hand_vertices": int(len(sd_hand))
    }
except Exception as e:
    signed_error = repr(e)

# Unsigned nearest distance for comparison.
tree = cKDTree(body_vertices)
d_unsigned, nn = tree.query(hand_vertices, k=1)

mesh_quality = {
    "body_path": str(body_path),
    "body_vertices": int(len(body_vertices)),
    "body_faces": int(len(body_faces)),
    "is_watertight": bool(body.is_watertight),
    "is_winding_consistent": bool(body.is_winding_consistent),
    "euler_number": safe_float(body.euler_number),
    "volume": safe_float(body.volume),
    "num_components": int(len(components)),
    "component_vertex_counts_top10": sorted(component_sizes, reverse=True)[:10],
    "bbox_extents": bbox_extents.tolist(),
    "bbox_diag": bbox_diag
}

unsigned_report = {
    "min": float(np.min(d_unsigned)),
    "p1": float(np.percentile(d_unsigned, 1)),
    "p5": float(np.percentile(d_unsigned, 5)),
    "p10": float(np.percentile(d_unsigned, 10)),
    "mean": float(np.mean(d_unsigned)),
    "within_003": int((d_unsigned < 0.003).sum()),
    "within_005": int((d_unsigned < 0.005).sum()),
    "within_01": int((d_unsigned < 0.01).sum()),
    "within_02": int((d_unsigned < 0.02).sum()),
    "within_05": int((d_unsigned < 0.05).sum())
}

# Decision logic.
if signed_error is not None:
    decision = "FAIL_SIGNED_DISTANCE_RUNTIME"
elif not body.is_watertight:
    decision = "SDF_UNRELIABLE_BODY_NOT_WATERTIGHT"
elif len(components) > 1:
    decision = "SDF_WEAK_BODY_MULTICOMPONENT"
else:
    neg = signed_report["hand_signed_distance"]["negative_count_lt_minus_005"]
    if neg > 50:
        decision = "SDF_RELIABLE_COLLISION_CONFIRMED"
    else:
        decision = "SDF_RELIABLE_LOW_COLLISION"

scene = trimesh.Scene()
scene.add_geometry(colorize(obj, [255, 255, 255, 35]), node_name="object_white")
scene.add_geometry(colorize(body, [0, 180, 255, 145]), node_name="body_blue")
scene.add_geometry(colorize(hand, [0, 255, 0, 120]), node_name="hand_green")

# Add probe points.
for item in signed_report.get("probe_points", []):
    rgba = [255, 255, 0, 255] if item["name"] == "bbox_center" else [255, 0, 255, 255]
    scene.add_geometry(make_sphere(item["point"], 0.01, rgba), node_name=item["name"])

visual_path = VIS / "aket01_gate_d_sandbox_v0_2a_sdf_sanity_audit.glb"
scene.export(visual_path)

report = {
    "case_id": "aket01",
    "stage": "Gate D sandbox v0.2a SDF sanity audit",
    "mesh_quality": mesh_quality,
    "unsigned_hand_to_body": unsigned_report,
    "signed_distance_error": signed_error,
    "signed_report": signed_report,
    "decision": decision,
    "visual": str(visual_path),
    "interpretation": [
        "If body is not watertight, signed-distance penetration depth should be treated as a warning, not final truth.",
        "If body is watertight and many hand points are deeply negative, collision is confirmed.",
        "This audit decides whether v0.3 should use signed-distance push-out or a fallback collision proxy."
    ]
}

report_path = MET / "aket01_gate_d_sandbox_v0_2a_sdf_sanity_report.json"
report_path.write_text(json.dumps(report, indent=2))

print("[OK] visual:", visual_path)
print("[OK] report:", report_path)
print("[decision]", decision)
print(json.dumps(report, indent=2)[:5000])
