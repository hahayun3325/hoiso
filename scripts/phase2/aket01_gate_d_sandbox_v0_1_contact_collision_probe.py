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
SANDBOX = AKET / "gate_d_sandbox_v0_1_contact_collision_probe"

VIS = SANDBOX / "visuals"
MET = SANDBOX / "metrics"
OUT = SANDBOX / "outputs"
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
        "within_003": int((d < 0.003).sum()),
        "within_005": int((d < 0.005).sum()),
        "within_01": int((d < 0.01).sum()),
        "within_02": int((d < 0.02).sum()),
        "within_05": int((d < 0.05).sum())
    }

def eval_hand_to_body(hand_pts, body_pts):
    tree = cKDTree(body_pts)
    d, nn = tree.query(hand_pts, k=1)
    return d, nn

hand_path = SEL_RUN / "guidance_out/aket01_hand.ply"
obj_path = SEL_RUN / "guidance_out/aket01_obj.ply"
body_path = ACTIVE / "body.ply"

hand = load_mesh(hand_path)
obj = load_mesh(obj_path)
body = load_mesh(body_path)

hand_pts, hand_idx = sample_vertices(hand, 12000, seed=1)
body_pts, body_idx = sample_vertices(body, 12000, seed=2)

d0, nn0 = eval_hand_to_body(hand_pts, body_pts)
order = np.argsort(d0)

# Use the same kind of verified local patch as scorer v0.
patch_n = 80
patch_hand = hand_pts[order[:patch_n]]
patch_body = body_pts[nn0[order[:patch_n]]]

# Direction from hand patch centroid to body patch centroid.
raw_vec = patch_body.mean(axis=0) - patch_hand.mean(axis=0)
raw_norm = float(np.linalg.norm(raw_vec))
if raw_norm > 1e-9:
    direction = raw_vec / raw_norm
else:
    direction = np.zeros(3)

# Keep this tiny. This is a probe, not a full optimizer.
max_step = min(raw_norm, 0.010)  # cap at 1 cm

alphas = [0.0, 0.25, 0.50, 0.75, 1.0]
rows = []

baseline = stats(d0)
baseline_close = baseline["within_003"]

best = None
for alpha in alphas:
    t = direction * (alpha * max_step)
    shifted_hand_pts = hand_pts + t[None, :]
    d, nn = eval_hand_to_body(shifted_hand_pts, body_pts)
    s = stats(d)

    # Score: prefer lower p5 and mean, but penalize too many very-close points.
    close_growth = max(0, s["within_003"] - baseline_close)
    score = -s["p5"] - 0.25 * s["mean"] - 0.002 * close_growth

    row = {
        "alpha": alpha,
        "translation": t.tolist(),
        "translation_norm": float(np.linalg.norm(t)),
        "score": float(score),
        "stats": s,
        "very_close_growth_vs_baseline": int(close_growth)
    }
    rows.append(row)
    if best is None or row["score"] > best["score"]:
        best = row

decision = "VISUAL_REVIEW_REQUIRED"
if best["alpha"] == 0.0:
    decision = "PASS_STABLE_NO_MOVE_BEST"
elif best["translation_norm"] <= 0.010 and best["very_close_growth_vs_baseline"] <= 10:
    decision = "PASS_TINY_CONTACT_UPDATE_SAFE"
else:
    decision = "REJECT_UPDATE_KEEP_ORIGINAL_CONTACT"

# Build visual scene.
scene = trimesh.Scene()
scene.add_geometry(colorize(obj, [255, 255, 255, 45]), node_name="guidance_object_white")
scene.add_geometry(colorize(body, [0, 180, 255, 135]), node_name="body_blue")
scene.add_geometry(colorize(hand, [0, 255, 0, 105]), node_name="original_hand_green")

best_hand = hand.copy()
best_t = np.array(best["translation"], dtype=float)
best_hand.apply_translation(best_t)
scene.add_geometry(colorize(best_hand, [255, 120, 0, 105]), node_name="best_probe_hand_orange")

# Mark original patch and best patch.
best_hand_pts = hand_pts + best_t[None, :]
d_best, nn_best = eval_hand_to_body(best_hand_pts, body_pts)
order_best = np.argsort(d_best)
best_patch_hand = best_hand_pts[order_best[:patch_n]]
best_patch_body = body_pts[nn_best[order_best[:patch_n]]]

for p in patch_hand[:30]:
    scene.add_geometry(make_sphere(p, 0.0045, [255, 0, 0, 220]), node_name="orig_hand_patch_red")
for p in patch_body[:30]:
    scene.add_geometry(make_sphere(p, 0.0045, [0, 0, 255, 220]), node_name="orig_body_patch_blue")

for p in best_patch_hand[:30]:
    scene.add_geometry(make_sphere(p, 0.0045, [255, 180, 0, 255]), node_name="best_hand_patch_yellow")
for p in best_patch_body[:30]:
    scene.add_geometry(make_sphere(p, 0.0045, [100, 0, 255, 255]), node_name="best_body_patch_purple")

visual_path = VIS / "aket01_gate_d_sandbox_v0_1_contact_collision_probe.glb"
scene.export(visual_path)

report = {
    "case_id": "aket01",
    "stage": "Gate D sandbox v0.1 contact/collision probe",
    "hand_path": str(hand_path),
    "object_path": str(obj_path),
    "body_path": str(body_path),
    "baseline_stats": baseline,
    "raw_contact_vector_norm": raw_norm,
    "max_step": max_step,
    "rows": rows,
    "best": best,
    "decision": decision,
    "visual": str(visual_path),
    "interpretation": [
        "This is a tiny probe, not full optimization.",
        "Green hand is original; orange hand is best tiny-update candidate.",
        "Red/blue markers show original contact patch.",
        "Yellow/purple markers show best candidate patch.",
        "If alpha=0 is best, that is still a useful result: current contact is already stable."
    ]
}

report_path = MET / "aket01_gate_d_sandbox_v0_1_report.json"
report_path.write_text(json.dumps(report, indent=2))

print("[OK] visual:", visual_path)
print("[OK] report:", report_path)
print("[decision]", decision)
print(json.dumps({
    "baseline": baseline,
    "best": best,
    "raw_contact_vector_norm": raw_norm,
    "max_step": max_step
}, indent=2))
