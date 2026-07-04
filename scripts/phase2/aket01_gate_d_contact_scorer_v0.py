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
GATED = AKET / "gate_d_contact_scorer_v0"

VIS = GATED / "visuals"
MET = GATED / "metrics"
OUT = GATED / "outputs"
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

def sample_vertices(mesh, n=12000, seed=0):
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

def stats(d):
    return {
        "min": float(np.min(d)),
        "p1": float(np.percentile(d, 1)),
        "p5": float(np.percentile(d, 5)),
        "p10": float(np.percentile(d, 10)),
        "mean": float(np.mean(d)),
        "within_005": int((d < 0.005).sum()),
        "within_01": int((d < 0.01).sum()),
        "within_02": int((d < 0.02).sum()),
        "within_05": int((d < 0.05).sum())
    }

hand_path = SEL_RUN / "guidance_out/aket01_hand.ply"
body_path = ACTIVE / "body.ply"
obj_path = SEL_RUN / "guidance_out/aket01_obj.ply"

hand = load_mesh(hand_path)
body = load_mesh(body_path)
obj = load_mesh(obj_path)

hand_pts, hand_idx = sample_vertices(hand, n=12000, seed=1)
body_pts, body_idx = sample_vertices(body, n=12000, seed=2)

tree = cKDTree(body_pts)
d, nn = tree.query(hand_pts, k=1)
order = np.argsort(d)

# Verified patch: nearest hand vertices to body.
patch_n = 80
patch_hand_pts = hand_pts[order[:patch_n]]
patch_body_pts = body_pts[nn[order[:patch_n]]]
patch_d = d[order[:patch_n]]

# Contact attraction loss: squared distance for verified patch.
l_attract_mean_sq = float(np.mean(patch_d ** 2))
patch_mean_distance = float(np.mean(patch_d))

# A simple collision warning proxy, not a true signed-distance collision metric.
# It flags very-close vertices that may be contact or shallow penetration.
very_close = d < 0.003
near_contact = d < 0.02

decision = "VISUAL_REVIEW_REQUIRED"
if patch_mean_distance < 0.015 and near_contact.sum() > 100:
    decision = "PASS_CONTACT_TARGET_READY_FOR_SANDBOX"
elif patch_mean_distance < 0.03:
    decision = "PARTIAL_CONTACT_TARGET_WEAK_BUT_USABLE"
else:
    decision = "FAIL_CONTACT_TARGET_TOO_FAR"

scene = trimesh.Scene()
scene.add_geometry(colorize(hand, [0, 255, 0, 135]), node_name="guidance_hand_green")
scene.add_geometry(colorize(obj, [255, 255, 255, 35]), node_name="guidance_object_white")
scene.add_geometry(colorize(body, [0, 180, 255, 145]), node_name="verified_body_blue")

# red = hand patch, blue = matched body patch
for p in patch_hand_pts[:40]:
    scene.add_geometry(make_sphere(p, 0.005, [255, 0, 0, 255]), node_name="verified_hand_patch_red")
for p in patch_body_pts[:40]:
    scene.add_geometry(make_sphere(p, 0.005, [0, 0, 255, 255]), node_name="verified_body_patch_blue")

visual_path = VIS / "aket01_gate_d_contact_scorer_v0_target.glb"
scene.export(visual_path)

target = {
    "case_id": "aket01",
    "stage": "Gate D contact scorer v0",
    "verified_contact": {
        "hand_source": str(hand_path),
        "object_part": "body",
        "object_part_path": str(body_path),
        "patch_n": patch_n,
        "patch_mean_distance": patch_mean_distance,
        "patch_l_attract_mean_squared": l_attract_mean_sq
    },
    "contact_stats_all_hand_to_body": stats(d),
    "contact_stats_patch": stats(patch_d),
    "very_close_proxy": {
        "threshold_m": 0.003,
        "count": int(very_close.sum()),
        "note": "This is not true penetration. It only flags very-close hand vertices."
    },
    "near_contact_proxy": {
        "threshold_m": 0.02,
        "count": int(near_contact.sum())
    },
    "decision": decision,
    "visual": str(visual_path),
    "next_step": "If visual patch is correct, run tiny contact/collision sandbox without changing object semantics."
}

target_path = OUT / "aket01_gate_d_contact_scorer_v0_target.json"
target_path.write_text(json.dumps(target, indent=2))

print("[OK] visual:", visual_path)
print("[OK] target:", target_path)
print("[decision]", decision)
print(json.dumps({
    "patch_mean_distance": patch_mean_distance,
    "patch_l_attract_mean_squared": l_attract_mean_sq,
    "all_hand_to_body": target["contact_stats_all_hand_to_body"],
    "patch": target["contact_stats_patch"],
    "very_close_proxy": target["very_close_proxy"],
    "near_contact_proxy": target["near_contact_proxy"]
}, indent=2))
