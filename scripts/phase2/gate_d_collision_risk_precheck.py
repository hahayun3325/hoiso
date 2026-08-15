from pathlib import Path
import json
import numpy as np
import trimesh

case = "alapuse01"
root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases") / case

orig_hand_path = root / "input/final_hand.ply"
opt_hand_path = root / "gate_d_optimization/selected_optimizer_v0_contact_only/hand_optimizer_v0_contact_only_selected.ply"
part_dir = root / "part_meshes_partfield_v2_vmap"

out_dir = root / "gate_d_optimization/collision_precheck_v1"
out_metrics = out_dir / "gate_d_collision_risk_precheck_v1.json"
out_dir.mkdir(parents=True, exist_ok=True)

object_part_names = ["screen", "keyboard_base", "hinge", "residual_uncertain"]
support_part_names = ["keyboard_base", "hinge"]

def load_mesh_points(path):
    mesh = trimesh.load(path, force="mesh", process=False)
    return mesh, np.asarray(mesh.vertices)

def concat_part_points(names):
    meshes = []
    for name in names:
        p = part_dir / f"{name}.ply"
        if p.exists():
            meshes.append(trimesh.load(p, force="mesh", process=False))
    if not meshes:
        raise FileNotFoundError(f"No part meshes found for {names}")
    mesh = trimesh.util.concatenate(meshes)
    return mesh, np.asarray(mesh.vertices)

def nearest_distances_chunked(query_points, target_points, chunk=256):
    out = []
    for i in range(0, len(query_points), chunk):
        q = query_points[i:i+chunk]
        diff = q[:, None, :] - target_points[None, :, :]
        d = np.linalg.norm(diff, axis=-1).min(axis=1)
        out.append(d)
    return np.concatenate(out, axis=0)

def summarize(name, d):
    thresholds = [0.003, 0.005, 0.010, 0.020, 0.030, 0.050]
    row = {
        "name": name,
        "num_vertices": int(len(d)),
        "min": float(np.min(d)),
        "p1": float(np.percentile(d, 1)),
        "p5": float(np.percentile(d, 5)),
        "mean": float(np.mean(d)),
    }
    for t in thresholds:
        row[f"num_within_{t:.3f}"] = int(np.sum(d <= t))
        row[f"ratio_within_{t:.3f}"] = float(np.mean(d <= t))
    return row

orig_hand, orig_pts = load_mesh_points(orig_hand_path)
opt_hand, opt_pts = load_mesh_points(opt_hand_path)

full_obj, full_obj_pts = concat_part_points(object_part_names)
support_obj, support_obj_pts = concat_part_points(support_part_names)

orig_full_d = nearest_distances_chunked(orig_pts, full_obj_pts)
opt_full_d = nearest_distances_chunked(opt_pts, full_obj_pts)

orig_support_d = nearest_distances_chunked(orig_pts, support_obj_pts)
opt_support_d = nearest_distances_chunked(opt_pts, support_obj_pts)

# Very-close risk: useful for non-watertight meshes where signed penetration is unreliable.
risk_threshold = 0.005
new_risk_ids = np.where((opt_full_d <= risk_threshold) & (orig_full_d > risk_threshold))[0]

shift = opt_pts - orig_pts
shift_norms = np.linalg.norm(shift, axis=1)

report = {
    "case_id": case,
    "precheck_type": "nearest_distance_collision_risk_non_watertight",
    "note": "This is not a true signed penetration test. It is a nearest-distance collision-risk precheck because the object parts are broken/non-watertight.",
    "inputs": {
        "original_hand": str(orig_hand_path),
        "optimized_hand": str(opt_hand_path),
        "object_parts": object_part_names,
        "support_parts": support_part_names
    },
    "global_hand_shift": {
        "mean_shift": float(np.mean(shift_norms)),
        "max_shift": float(np.max(shift_norms)),
        "expected_uniform_shift": "optimizer v0 uses global hand translation only"
    },
    "full_object_distance_original": summarize("original_hand_to_full_object", orig_full_d),
    "full_object_distance_optimized": summarize("optimized_hand_to_full_object", opt_full_d),
    "support_region_distance_original": summarize("original_hand_to_keyboard_base_plus_hinge", orig_support_d),
    "support_region_distance_optimized": summarize("optimized_hand_to_keyboard_base_plus_hinge", opt_support_d),
    "new_very_close_vertices": {
        "threshold": risk_threshold,
        "count": int(len(new_risk_ids)),
        "ratio": float(len(new_risk_ids) / max(len(opt_pts), 1)),
        "vertex_ids": new_risk_ids[:200].astype(int).tolist()
    },
    "decision_hint": "Pass if contact improves, global shift is small, and new very-close full-object vertices are not visually unsafe. Inspect marker scene next."
}

out_metrics.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
print("[OK] wrote", out_metrics)
