from pathlib import Path
import json
import numpy as np
import trimesh

case = "alapuse01"
root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases") / case

hand_path = root / "input/final_hand.ply"
part_dir = root / "part_meshes_partfield_v2_vmap"

target_path = root / "gate_d_optimization/targets/gate_d_contact_target_dryrun_v1.json"
patch_report_path = root / "gate_b_contact/metrics/gate_c_finger_patch_local_region_check.json"
decision_path = root / "gate_d_optimization/metrics/gate_d_contact_only_smoke_preview_decision_v1.json"

out_dir = root / "gate_d_optimization/optimizer_v1_exploratory_contact_only"
visual_dir = out_dir / "visuals"
metrics_path = out_dir / "gate_d_optimizer_v1_exploratory_contact_only_metrics.json"

out_dir.mkdir(parents=True, exist_ok=True)
visual_dir.mkdir(parents=True, exist_ok=True)

hand = trimesh.load(hand_path, force="mesh", process=False)
hand_points = np.asarray(hand.vertices)

target = json.loads(target_path.read_text())
patch = json.loads(patch_report_path.read_text())
decision = json.loads(decision_path.read_text())

alpha_cap = float(decision["selected_alpha"])

center_idx = int(patch["center_hand_vertex"])
center_xyz = hand_points[center_idx]
patch_radius = float(patch["patch_radius"])

patch_d = np.linalg.norm(hand_points - center_xyz[None, :], axis=1)
patch_ids = np.where(patch_d <= patch_radius)[0]

region_parts = target["contact_pair"]["support_parts"]
region_meshes = []
for name in region_parts:
    p = part_dir / f"{name}.ply"
    if p.exists():
        region_meshes.append(trimesh.load(p, force="mesh", process=False))

region = trimesh.util.concatenate(region_meshes)
region_points = np.asarray(region.vertices)

direction = np.asarray(target["attraction_direction_hand_to_object"], dtype=float)
direction = direction / max(np.linalg.norm(direction), 1e-8)
base_dist = float(target["distance"])

def nearest_vertex_distances(points, region_points):
    diff = points[:, None, :] - region_points[None, :, :]
    return np.linalg.norm(diff, axis=-1).min(axis=1)

# Exploratory v1 contact-only line search. Keep the cap at selected_alpha=0.75. Object frozen, joint frozen.
alphas = np.linspace(0.0, alpha_cap, 7).tolist()

rows = []
for a in alphas:
    shift = a * base_dist * direction
    moved_points = hand_points + shift[None, :]
    moved_patch_points = moved_points[patch_ids]

    d = nearest_vertex_distances(moved_patch_points, region_points)
    contact_loss = float(np.mean(d ** 2))

    # Tiny regularizer only to record movement size; contact-only objective still dominates.
    shift_norm = float(np.linalg.norm(shift))
    total_loss = contact_loss

    rows.append({
        "alpha": float(a),
        "shift_norm": shift_norm,
        "patch_min_distance": float(np.min(d)),
        "patch_p1_distance": float(np.percentile(d, 1)),
        "patch_p5_distance": float(np.percentile(d, 5)),
        "patch_mean_distance": float(np.mean(d)),
        "l_attract_mean_squared": contact_loss,
        "total_loss_contact_only": total_loss,
        "ratio_patch_vertices_within_0.03": float(np.mean(d <= 0.03)),
        "ratio_patch_vertices_within_0.05": float(np.mean(d <= 0.05))
    })

best = min(rows, key=lambda r: r["total_loss_contact_only"])
best_alpha = float(best["alpha"])
best_shift = best_alpha * base_dist * direction

optimized_hand = hand.copy()
optimized_hand.vertices = hand_points + best_shift[None, :]

out_hand = out_dir / "hand_optimizer_v1_exploratory_contact_only.ply"
optimized_hand.export(out_hand)

scene = trimesh.Scene()
scene.add_geometry(optimized_hand, node_name="hand_optimizer_v1_exploratory_contact_only")
for name in region_parts:
    p = part_dir / f"{name}.ply"
    if p.exists():
        scene.add_geometry(trimesh.load(p, force="mesh", process=False), node_name=name)

out_scene = visual_dir / "scene_optimizer_v1_exploratory_contact_only.glb"
scene.export(out_scene)

report = {
    "case_id": case,
    "optimizer": "gate_d_optimizer_v1_exploratory_contact_only_line_search",
    "should_modify_original_meshes": False,
    "allowed_motion": "global_hand_translation_only",
    "object_motion": "none",
    "collision_loss": "disabled",
    "joint_update": "disabled",
    "alpha_cap": alpha_cap,
    "base_distance": base_dist,
    "direction": direction.tolist(),
    "best_alpha": best_alpha,
    "best_shift_norm": float(np.linalg.norm(best_shift)),
    "best_row": best,
    "all_rows": rows,
    "outputs": {
        "optimized_hand": str(out_hand),
        "optimized_scene": str(out_scene)
    },
    "decision_hint": "Visually inspect optimized_scene before accepting. Do not overwrite original meshes."
}

metrics_path.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
print("[OK] wrote", out_hand)
print("[OK] wrote", out_scene)
print("[OK] wrote", metrics_path)
