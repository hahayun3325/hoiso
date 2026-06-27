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

out_dir = root / "gate_d_optimization/smoke_contact_only_v1"
visual_dir = out_dir / "visuals"
metrics_path = out_dir / "gate_d_contact_only_smoke_preview_metrics.json"

out_dir.mkdir(parents=True, exist_ok=True)
visual_dir.mkdir(parents=True, exist_ok=True)

hand = trimesh.load(hand_path, force="mesh", process=False)
hand_points = np.asarray(hand.vertices)

target = json.loads(target_path.read_text())
patch = json.loads(patch_report_path.read_text())

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

alphas = [0.0, 0.25, 0.50, 0.75, 1.00]
rows = []

for a in alphas:
    shift = a * base_dist * direction

    moved_hand = hand.copy()
    moved_hand.vertices = hand_points + shift[None, :]

    moved_points = np.asarray(moved_hand.vertices)
    moved_patch_points = moved_points[patch_ids]
    d = nearest_vertex_distances(moved_patch_points, region_points)

    out_hand = out_dir / f"hand_contact_only_alpha_{a:.2f}.ply"
    moved_hand.export(out_hand)

    scene = trimesh.Scene()
    scene.add_geometry(moved_hand, node_name=f"moved_hand_alpha_{a:.2f}")

    for name in region_parts:
        p = part_dir / f"{name}.ply"
        if p.exists():
            scene.add_geometry(trimesh.load(p, force="mesh", process=False), node_name=name)

    scene_path = visual_dir / f"scene_contact_only_alpha_{a:.2f}.glb"
    scene.export(scene_path)

    rows.append({
        "alpha": a,
        "shift_norm": float(np.linalg.norm(shift)),
        "out_hand": str(out_hand),
        "scene": str(scene_path),
        "patch_min_distance": float(np.min(d)),
        "patch_p1_distance": float(np.percentile(d, 1)),
        "patch_p5_distance": float(np.percentile(d, 5)),
        "patch_mean_distance": float(np.mean(d)),
        "l_attract_mean_squared": float(np.mean(d ** 2)),
        "ratio_patch_vertices_within_0.03": float(np.mean(d <= 0.03)),
        "ratio_patch_vertices_within_0.05": float(np.mean(d <= 0.05))
    })

report = {
    "case_id": case,
    "smoke_test": "contact_only_global_hand_translation_preview",
    "should_modify_original_meshes": False,
    "warning": "This only exports temporary moved hand copies. It is not the final optimizer.",
    "contact_pair": target["contact_pair"],
    "base_distance": base_dist,
    "direction": direction.tolist(),
    "rows": rows
}

metrics_path.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
print("[OK] wrote", metrics_path)
