from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT_ROOT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit"
MANIFEST = FIT_ROOT / "metrics/standalone_fitter_input_manifest.json"
ACTIVE = CASE_ROOT / "integrated_gates/gate_a_part_repair/active_clean_parts"

GATE_C = CASE_ROOT / "integrated_gates/gate_c_v3_1_local_mesh_patch/metrics/gate_c_v3_1_local_mesh_patch_check.json"
OUT = CASE_ROOT / "integrated_gates/gate_d_contact_scorer_v0"
OUT_METRICS = OUT / "metrics"
OUT_VIS = OUT / "visuals"
OUT_OUTPUTS = OUT / "outputs"

for p in [OUT_METRICS, OUT_VIS, OUT_OUTPUTS]:
    p.mkdir(parents=True, exist_ok=True)

def load_mesh(path):
    obj = trimesh.load(path, force=None, process=False)
    if isinstance(obj, trimesh.Scene):
        geoms = [
            g for g in obj.geometry.values()
            if hasattr(g, "vertices") and len(g.vertices) > 0
        ]
        return trimesh.util.concatenate(geoms)
    return obj

def colorize(mesh, rgba):
    m = mesh.copy()
    m.visual.vertex_colors = rgba
    return m

def marker(center, radius, rgba):
    s = trimesh.creation.icosphere(subdivisions=2, radius=radius)
    s.apply_translation(np.asarray(center, dtype=float))
    s.visual.vertex_colors = rgba
    return s

data = json.loads(MANIFEST.read_text())
paths = {k: Path(v["path"]) for k, v in data["paths"].items() if v["exists"]}

gate_c = json.loads(GATE_C.read_text())

screen = load_mesh(ACTIVE / "screen.ply")
base = load_mesh(ACTIVE / "keyboard_base.ply")
hinge = load_mesh(ACTIVE / "hinge.ply")
hand = load_mesh(paths["guidance_hand"])

screen_pts = np.asarray(screen.vertices, dtype=float)
hand_pts = np.asarray(hand.vertices, dtype=float)

patch_ids = gate_c["nearest_1_percent_patch"]["hand_vertex_indices_first100"]
patch_ids = np.asarray(patch_ids, dtype=int)

patch_hand_pts = hand_pts[patch_ids]

tree = cKDTree(screen_pts)
d, screen_nn_idx = tree.query(patch_hand_pts, k=1)
patch_screen_pts = screen_pts[screen_nn_idx]

# Contact-aware scorer v0.
# This is diagnostic only. It does not move hand or object yet.
target_band_min = 0.003
target_band_max = 0.020

too_far = np.maximum(d - target_band_max, 0.0)
too_close = np.maximum(target_band_min - d, 0.0)

l_attract = float(np.mean(too_far ** 2))
l_collision_proxy = float(np.mean(too_close ** 2))
l_contact_band = float(l_attract + l_collision_proxy)

metrics = {
    "case_id": "alapuse01",
    "stage": "Gate D contact-aware scorer v0",
    "input_contact": "Gate C v3.1 nearest hand-mesh patch to active screen",
    "object_seed": "v0 dry-run active clean parts",
    "num_patch_vertices": int(len(patch_ids)),
    "target_band_m": {
        "min": target_band_min,
        "max": target_band_max
    },
    "distance_stats": {
        "min": float(d.min()),
        "p1": float(np.percentile(d, 1)),
        "p5": float(np.percentile(d, 5)),
        "p10": float(np.percentile(d, 10)),
        "mean": float(d.mean()),
        "max": float(d.max())
    },
    "threshold_counts": {
        "within_5mm": int((d <= 0.005).sum()),
        "within_10mm": int((d <= 0.010).sum()),
        "within_20mm": int((d <= 0.020).sum()),
        "within_30mm": int((d <= 0.030).sum())
    },
    "loss_terms": {
        "l_attract_farther_than_20mm": l_attract,
        "l_collision_proxy_closer_than_3mm": l_collision_proxy,
        "l_contact_band_total": l_contact_band
    },
    "decision_rule": {
        "pass": "patch is mostly within 20mm and visual markers stay on intended contact region",
        "warning": "large closer-than-3mm count indicates possible penetration",
        "fail": "patch distances mostly larger than 30mm or visual region wrong"
    }
}

if metrics["threshold_counts"]["within_20mm"] >= max(3, int(0.5 * len(patch_ids))):
    decision = "PASS_CONTACT_SCORER_V0_PATCH_USABLE"
else:
    decision = "FAIL_CONTACT_SCORER_V0_PATCH_TOO_FAR"

if metrics["threshold_counts"]["within_5mm"] >= int(0.3 * len(patch_ids)):
    penetration_warning = True
else:
    penetration_warning = False

metrics["decision"] = decision
metrics["penetration_warning"] = penetration_warning
metrics["next_step"] = (
    "contact-aware scorer v0.1 dry-run with small loss-weight sweep"
    if decision.startswith("PASS")
    else "return to Gate C patch selection"
)

# Save target pairs for future optimizer.
target = {
    "case_id": "alapuse01",
    "stage": "verified_contact_patch_target_v0",
    "source": "Gate C v3.1 local hand-mesh patch",
    "hand_vertex_indices": patch_ids.astype(int).tolist(),
    "nearest_screen_vertex_indices": screen_nn_idx.astype(int).tolist(),
    "hand_patch_points": patch_hand_pts.tolist(),
    "screen_target_points": patch_screen_pts.tolist(),
    "target_band_m": {
        "min": target_band_min,
        "max": target_band_max
    },
    "semantic_contact": {
        "hand": "right",
        "contact_region": "local hand mesh patch",
        "object_part": "screen",
        "object_surface": "outer_top_lid_or_screen_region"
    }
}

out_metrics = OUT_METRICS / "gate_d_contact_scorer_v0_metrics.json"
out_target = OUT_OUTPUTS / "verified_contact_patch_target_v0.json"
out_metrics.write_text(json.dumps(metrics, indent=2))
out_target.write_text(json.dumps(target, indent=2))

scene = trimesh.Scene()
scene.add_geometry(colorize(screen, [0, 0, 255, 140]), node_name="active_screen_blue")
scene.add_geometry(colorize(base, [255, 140, 0, 170]), node_name="active_keyboard_base_orange")
scene.add_geometry(colorize(hinge, [255, 0, 255, 220]), node_name="active_hinge_magenta")
scene.add_geometry(colorize(hand, [0, 255, 0, 90]), node_name="guidance_hand_green")

for i, p in enumerate(patch_hand_pts):
    scene.add_geometry(marker(p, 0.004, [255, 0, 0, 255]), node_name=f"contact_hand_patch_red_{i:03d}")

for i, p in enumerate(patch_screen_pts):
    scene.add_geometry(marker(p, 0.0035, [0, 0, 255, 255]), node_name=f"contact_screen_target_blue_{i:03d}")

out_glb = OUT_VIS / "gate_d_contact_scorer_v0_contact_target.glb"
scene.export(out_glb)

print("[OK] wrote", out_metrics)
print("[OK] wrote", out_target)
print("[OK] wrote", out_glb)
print("[DECISION]", metrics["decision"])
print(json.dumps(metrics, indent=2))
