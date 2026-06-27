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
out_path = root / "gate_d_optimization/metrics/gate_d_contact_loss_precheck_v1.json"

hand = trimesh.load(hand_path, force="mesh", process=False)
hand_points = np.asarray(hand.vertices)

target = json.loads(target_path.read_text())
patch = json.loads(patch_report_path.read_text())

center_idx = int(patch["center_hand_vertex"])
center_xyz = hand_points[center_idx]
patch_radius = float(patch["patch_radius"])

patch_d = np.linalg.norm(hand_points - center_xyz[None, :], axis=1)
patch_ids = np.where(patch_d <= patch_radius)[0]
patch_points = hand_points[patch_ids]

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

# Virtual shifts only. Do not modify or save hand/object meshes.
alphas = [0.0, 0.25, 0.50, 0.75, 1.00]
rows = []

for a in alphas:
    shift = a * base_dist * direction
    shifted = patch_points + shift[None, :]
    d = nearest_vertex_distances(shifted, region_points)
    rows.append({
        "alpha": a,
        "virtual_shift_norm": float(np.linalg.norm(shift)),
        "patch_min_distance": float(np.min(d)),
        "patch_p1_distance": float(np.percentile(d, 1)),
        "patch_p5_distance": float(np.percentile(d, 5)),
        "patch_mean_distance": float(np.mean(d)),
        "l_attract_mean_squared": float(np.mean(d ** 2)),
        "num_patch_vertices": int(len(patch_points)),
        "ratio_patch_vertices_within_0.03": float(np.mean(d <= 0.03)),
        "ratio_patch_vertices_within_0.05": float(np.mean(d <= 0.05))
    })

out = {
    "case_id": case,
    "precheck_type": "virtual_contact_attraction_loss",
    "should_modify_meshes": False,
    "contact_pair": target["contact_pair"],
    "base_distance": base_dist,
    "patch_radius": patch_radius,
    "num_patch_vertices": int(len(patch_points)),
    "direction": direction.tolist(),
    "loss_curve": rows,
    "decision_hint": "If l_attract_mean_squared decreases as alpha increases, the attraction target is numerically sensible for a later optimizer smoke test."
}

out_path.write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
