from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

DATA = Path("/home/fredcui/foho_phase0")
case = "alapuse02_v3c"
token = "alapuse02v3c"

run_root = DATA / "phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse02_v3c_selector_v41_refined_pipeline"
case_root = DATA / "phase2_gateA_part_recon/cases" / case
exp_dir = case_root / "gate_c_experiment"
part_dir = case_root / "part_meshes_partfield_n2_vmap"
probe_dir = case_root / "integrated_gates/gate_c_v0_1_hand_scale_root_rescue_probe"

visual_dir = probe_dir / "visuals"
metric_dir = probe_dir / "metrics"
visual_dir.mkdir(parents=True, exist_ok=True)
metric_dir.mkdir(parents=True, exist_ok=True)

hand_path = run_root / f"guidance_out/{token}_hand.ply"
T_path = exp_dir / f"h2m_object_only_out/{token}_object_only_hoi_mesh.npy"

hand0 = trimesh.load(hand_path, process=False)
T = np.load(T_path)

screen = trimesh.load(part_dir / "screen_lid.ply", process=False)
base = trimesh.load(part_dir / "keyboard_base.ply", process=False)
screen.apply_transform(T)
base.apply_transform(T)

screen_pts = np.asarray(screen.vertices)
screen_tree = cKDTree(screen_pts)

# MANO fingertip indices: thumb, index, middle, ring, pinky
fingertip_idx = [744, 320, 443, 554, 671]
fingertip_names = ["thumb", "index", "middle", "ring", "pinky"]

if len(hand0.vertices) <= max(fingertip_idx):
    raise ValueError("Hand mesh does not have expected MANO fingertip indices.")

hand_vertices0 = np.asarray(hand0.vertices)
tips0 = hand_vertices0[fingertip_idx]

# Use hand centroid as simple scale center for this diagnostic.
# This is not a final physical optimizer; it is only a bounded rescue probe.
center = hand_vertices0.mean(axis=0)

scale_candidates = [1.00, 0.70, 0.60, 0.50, 0.45, 0.40, 0.35]
clip_candidates_m = [0.00, 0.04, 0.08, 0.12]
results = []

def color_mesh(mesh, rgba):
    m = mesh.copy()
    m.visual.vertex_colors = rgba
    return m

def transform_hand(scale, translation):
    h = hand0.copy()
    v = np.asarray(h.vertices)
    v2 = (v - center) * scale + center + translation
    h.vertices = v2
    return h

for s in scale_candidates:
    scaled_tips = (tips0 - center) * s + center

    d, nn = screen_tree.query(scaled_tips)
    best_i = int(np.argmin(d))
    best_tip = scaled_tips[best_i]
    target = screen_pts[nn[best_i]]
    full_vec = target - best_tip
    full_len = float(np.linalg.norm(full_vec))

    for clip in clip_candidates_m + [full_len]:
        if full_len < 1e-8:
            trans = np.zeros(3)
        else:
            use_len = min(clip, full_len)
            trans = full_vec / full_len * use_len

        h = transform_hand(s, trans)
        tips = np.asarray(h.vertices)[fingertip_idx]
        d2, _ = screen_tree.query(tips)

        result = {
            "scale": float(s),
            "translation_norm_m": float(np.linalg.norm(trans)),
            "full_required_translation_m": full_len,
            "best_fingertip": fingertip_names[best_i],
            "screen_lid_min_cm": float(d2.min() * 100.0),
            "screen_lid_mean_cm": float(d2.mean() * 100.0),
            "per_fingertip_screen_cm": {
                name: float(dist * 100.0)
                for name, dist in zip(fingertip_names, d2)
            }
        }

        # Prefer low distance, but penalize huge scale changes and large translations.
        result["score"] = (
            result["screen_lid_min_cm"]
            + 30.0 * abs(1.0 - s)
            + 100.0 * max(0.0, result["translation_norm_m"] - 0.12)
        )
        results.append(result)

# sort by score
results = sorted(results, key=lambda r: r["score"])
best = results[0]

# export scenes: no move, best, and full-snap debug
def export_scene(name, scale, translation):
    h = transform_hand(scale, translation)
    h = color_mesh(h, [255, 80, 80, 255])
    sc = color_mesh(screen, [80, 140, 255, 255])
    ba = color_mesh(base, [80, 220, 120, 255])
    scene = trimesh.Scene([h, sc, ba])
    out = visual_dir / f"{name}.glb"
    scene.export(out)
    return str(out)

# no move
export_scene("v0_1_no_move_current_frame", 1.0, np.zeros(3))

# best transform
best_scale = best["scale"]
scaled_tips = (tips0 - center) * best_scale + center
d, nn = screen_tree.query(scaled_tips)
best_i = int(np.argmin(d))
best_tip = scaled_tips[best_i]
target = screen_pts[nn[best_i]]
full_vec = target - best_tip
full_len = float(np.linalg.norm(full_vec))
if full_len < 1e-8:
    best_trans = np.zeros(3)
else:
    best_trans = full_vec / full_len * min(best["translation_norm_m"], full_len)

best["best_scene"] = export_scene("v0_1_best_hand_scale_root_probe", best_scale, best_trans)

# full snap debug for the same best scale
if full_len < 1e-8:
    full_trans = np.zeros(3)
else:
    full_trans = full_vec
best["full_snap_debug_scene"] = export_scene("v0_1_full_snap_debug_not_final", best_scale, full_trans)

report = {
    "case": case,
    "decision": "HAND_SCALE_ROOT_RESCUE_PROBE_ONLY_NOT_FINAL_GATE_C",
    "input_hand": str(hand_path),
    "part_dir": str(part_dir),
    "transform_T": str(T_path),
    "scale_candidates": scale_candidates,
    "clip_candidates_m": clip_candidates_m,
    "best": best,
    "top10": results[:10],
    "decision_rule": {
        "pass_diagnostic_only_if": "best has plausible scale >=0.45 and translation <=0.12m and visual contact is on screen_lid",
        "freeze_if": "best requires scale <0.45 or translation >0.12m or still does not visually contact screen_lid",
        "important": "This probe is not final Gate C. It only tests whether the shared-frame failure is recoverable by hand scale/root correction."
    }
}

out = metric_dir / "alapuse02_v3c_gate_c_v0_1_hand_scale_root_rescue_probe_report.json"
out.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
print("[OK] wrote", out)
