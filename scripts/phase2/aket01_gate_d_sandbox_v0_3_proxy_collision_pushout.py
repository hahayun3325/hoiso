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
V03 = AKET / "gate_d_sandbox_v0_3_proxy_collision_pushout"

VIS = V03 / "visuals"
MET = V03 / "metrics"
OUT = V03 / "outputs"
VIS.mkdir(parents=True, exist_ok=True)
MET.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

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

def make_sphere(center, radius, rgba):
    s = trimesh.creation.icosphere(subdivisions=2, radius=radius)
    s.apply_translation(np.asarray(center))
    s.visual.vertex_colors = rgba
    return s

def largest_component(mesh):
    comps = mesh.split(only_watertight=False)
    if not comps:
        return mesh
    comps = sorted(comps, key=lambda m: len(m.vertices), reverse=True)
    return comps[0]

def orient_normals_outward(points, normals, centroid):
    # Make normals roughly point away from object center.
    v = points - centroid[None, :]
    flip = np.einsum("ij,ij->i", v, normals) < 0
    normals = normals.copy()
    normals[flip] *= -1.0
    return normals

def surface_proxy(hand_mesh, body_mesh, n_surface=50000, seed=0):
    # Sample dense surface points from body and get face normals.
    surf_pts, face_idx = trimesh.sample.sample_surface(body_mesh, n_surface, seed=seed)
    face_normals = np.asarray(body_mesh.face_normals)[face_idx]
    face_normals = orient_normals_outward(
        surf_pts,
        face_normals,
        np.asarray(body_mesh.vertices).mean(axis=0),
    )

    tree = cKDTree(surf_pts)
    hand_pts = np.asarray(hand_mesh.vertices)
    d_unsigned, nn = tree.query(hand_pts, k=1)

    nearest_pts = surf_pts[nn]
    nearest_normals = face_normals[nn]

    # Signed local proxy:
    # positive = outside along outward normal;
    # negative = likely inside / penetrating.
    signed_proxy = np.einsum("ij,ij->i", hand_pts - nearest_pts, nearest_normals)

    return {
        "hand_pts": hand_pts,
        "nearest_pts": nearest_pts,
        "nearest_normals": nearest_normals,
        "unsigned": d_unsigned,
        "signed_proxy": signed_proxy,
    }

def stats(unsigned, signed_proxy):
    return {
        "unsigned_min": float(np.min(unsigned)),
        "unsigned_p1": float(np.percentile(unsigned, 1)),
        "unsigned_p5": float(np.percentile(unsigned, 5)),
        "unsigned_p10": float(np.percentile(unsigned, 10)),
        "unsigned_mean": float(np.mean(unsigned)),
        "within_003": int((unsigned < 0.003).sum()),
        "within_005": int((unsigned < 0.005).sum()),
        "within_01": int((unsigned < 0.01).sum()),
        "within_02": int((unsigned < 0.02).sum()),
        "within_05": int((unsigned < 0.05).sum()),
        "proxy_min": float(np.min(signed_proxy)),
        "proxy_p1": float(np.percentile(signed_proxy, 1)),
        "proxy_p5": float(np.percentile(signed_proxy, 5)),
        "proxy_mean": float(np.mean(signed_proxy)),
        "proxy_negative_lt_0": int((signed_proxy < 0.0).sum()),
        "proxy_negative_lt_minus_002": int((signed_proxy < -0.002).sum()),
        "proxy_negative_lt_minus_005": int((signed_proxy < -0.005).sum()),
    }

def translate_mesh(mesh, t):
    m = mesh.copy()
    m.apply_translation(np.asarray(t))
    return m

hand_path = SEL_RUN / "guidance_out/aket01_hand.ply"
obj_path = SEL_RUN / "guidance_out/aket01_obj.ply"
body_path = ACTIVE / "body.ply"

hand = load_mesh(hand_path)
obj = load_mesh(obj_path)
body_raw = load_mesh(body_path)
body = largest_component(body_raw)

body_largest_path = OUT / "aket01_body_largest_component_for_proxy.ply"
body.export(body_largest_path)

base = surface_proxy(hand, body, seed=10)
base_stats = stats(base["unsigned"], base["signed_proxy"])

# Candidate push-out direction.
# Use only points that are likely inside by local normal proxy.
deep = base["signed_proxy"] < -0.005
moderate = base["signed_proxy"] < -0.002

if deep.sum() >= 5:
    active = deep
elif moderate.sum() >= 5:
    active = moderate
else:
    active = base["unsigned"] < 0.01

# Push hand outward along local body normals.
needed = np.maximum(0.0, 0.003 - base["signed_proxy"][active])
raw_push_vecs = needed[:, None] * base["nearest_normals"][active]
push_vec = raw_push_vecs.mean(axis=0) if len(raw_push_vecs) else np.zeros(3)

# Clip large accidental pushes.
norm = float(np.linalg.norm(push_vec))
max_push = 0.035  # 3.5 cm diagnostic limit
if norm > max_push:
    push_vec = push_vec / norm * max_push

alphas = [0.0, 0.25, 0.5, 0.75, 1.0]
candidates = []

for alpha in alphas:
    t = alpha * push_vec
    h = translate_mesh(hand, t)
    prox = surface_proxy(h, body, seed=10)
    st = stats(prox["unsigned"], prox["signed_proxy"])

    # Prefer fewer proxy-negative points, but keep contact close.
    # The term within_05 keeps the hand from being pushed away too much.
    score = (
        -5.0 * st["proxy_negative_lt_minus_005"]
        -2.0 * st["proxy_negative_lt_minus_002"]
        +0.5 * st["within_05"]
        -100.0 * float(np.linalg.norm(t))
    )

    candidates.append({
        "alpha": alpha,
        "translation": t.tolist(),
        "translation_norm": float(np.linalg.norm(t)),
        "stats": st,
        "score": float(score),
    })

best = max(candidates, key=lambda x: x["score"])
best_hand = translate_mesh(hand, np.asarray(best["translation"]))

# Visual scene.
scene = trimesh.Scene()
scene.add_geometry(colorize(obj, [255, 255, 255, 35]), node_name="guidance_object_white")
scene.add_geometry(colorize(body, [0, 180, 255, 145]), node_name="largest_body_blue")
scene.add_geometry(colorize(hand, [0, 255, 0, 75]), node_name="original_hand_green_transparent")
scene.add_geometry(colorize(best_hand, [255, 140, 0, 155]), node_name="best_proxy_pushed_hand_orange")

# Marker visualization on original hand: suspected proxy penetrations.
idx_deep = np.where(base["signed_proxy"] < -0.005)[0]
idx_mod = np.where((base["signed_proxy"] < -0.002) & (base["signed_proxy"] >= -0.005))[0]

for i in idx_deep[:120]:
    scene.add_geometry(make_sphere(base["hand_pts"][i], 0.0045, [255, 0, 0, 255]), node_name="deep_proxy_red")

for i in idx_mod[:120]:
    scene.add_geometry(make_sphere(base["hand_pts"][i], 0.0035, [255, 255, 0, 230]), node_name="moderate_proxy_yellow")

visual_path = VIS / "aket01_gate_d_sandbox_v0_3_proxy_collision_pushout.glb"
scene.export(visual_path)

# Decision.
base_deep = base_stats["proxy_negative_lt_minus_005"]
best_deep = best["stats"]["proxy_negative_lt_minus_005"]
base_within05 = base_stats["within_05"]
best_within05 = best["stats"]["within_05"]

if best_deep < base_deep and best_within05 >= 0.75 * max(1, base_within05):
    decision = "PASS_PROXY_PUSHOUT_REDUCES_COLLISION_KEEP_CONTACT"
elif best_deep < base_deep:
    decision = "PARTIAL_PROXY_PUSHOUT_REDUCES_COLLISION_BUT_WEAKENS_CONTACT"
elif base_deep == 0:
    decision = "PASS_PROXY_NO_DEEP_COLLISION_FOUND"
else:
    decision = "FAIL_PROXY_NO_SAFE_PUSHOUT"

report = {
    "case_id": "aket01",
    "stage": "Gate D sandbox v0.3 robust proxy collision push-out",
    "hand_path": str(hand_path),
    "body_path": str(body_path),
    "body_largest_component_path": str(body_largest_path),
    "object_path": str(obj_path),
    "body_raw_is_watertight": bool(body_raw.is_watertight),
    "body_largest_is_watertight": bool(body.is_watertight),
    "body_raw_components": [int(len(c.vertices)) for c in body_raw.split(only_watertight=False)],
    "base_stats": base_stats,
    "push_vector": push_vec.tolist(),
    "push_vector_norm": float(np.linalg.norm(push_vec)),
    "candidates": candidates,
    "best": best,
    "decision": decision,
    "visual": str(visual_path),
    "interpretation": [
        "This is a fallback collision proxy because v0.2a showed raw SDF is unreliable.",
        "It uses largest body component + nearest surface local normal push-out.",
        "Green is original hand. Orange is best proxy-corrected hand.",
        "Red/yellow markers indicate suspected proxy penetration regions on the original hand.",
        "This is still a sandbox diagnostic, not the final optimizer."
    ]
}

report_path = MET / "aket01_gate_d_sandbox_v0_3_proxy_collision_pushout_report.json"
report_path.write_text(json.dumps(report, indent=2))

print("[OK] visual:", visual_path)
print("[OK] report:", report_path)
print("[decision]", decision)
print("[base_deep]", base_deep, "[best_deep]", best_deep)
print("[base_within05]", base_within05, "[best_within05]", best_within05)
print("[best]", json.dumps(best, indent=2))
