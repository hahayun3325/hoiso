from pathlib import Path
import json
import numpy as np
import trimesh

case = "alapuse01"
root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases") / case

hand_path = root / "input/final_hand.ply"
part_dir = root / "part_meshes_partfield_v2_vmap"
local_report = root / "gate_b_contact/metrics/gate_c_local_contact_region_precheck.json"
out_path = root / "gate_b_contact/metrics/gate_c_finger_patch_local_region_check.json"

hand = trimesh.load(hand_path, force="mesh", process=False)
hand_points = np.asarray(hand.vertices)

report = json.loads(local_report.read_text())
center_idx = int(report["nearest_hand_vertex"])
center_xyz = hand_points[center_idx]

# Approximate local finger patch by Euclidean radius around nearest hand vertex.
# This is not perfect finger segmentation, but better than one vertex.
patch_radius = 0.035
patch_d = np.linalg.norm(hand_points - center_xyz[None, :], axis=1)
patch_ids = np.where(patch_d <= patch_radius)[0]
patch_points = hand_points[patch_ids]

region_parts = ["keyboard_base", "hinge"]
meshes = []
for name in region_parts:
    p = part_dir / f"{name}.ply"
    if p.exists():
        meshes.append(trimesh.load(p, force="mesh", process=False))

region = trimesh.util.concatenate(meshes)
region_points = np.asarray(region.vertices)

diff = patch_points[:, None, :] - region_points[None, :, :]
dmat = np.linalg.norm(diff, axis=-1)
d = dmat.min(axis=1)

thresholds = [0.02, 0.03, 0.05, 0.08]
threshold_counts = {
    f"num_patch_vertices_within_{t:.2f}": int(np.sum(d <= t))
    for t in thresholds
}
threshold_ratios = {
    f"ratio_patch_vertices_within_{t:.2f}": float(np.mean(d <= t))
    for t in thresholds
}

nearest_patch_local_idx = int(np.argmin(d))
nearest_hand_idx = int(patch_ids[nearest_patch_local_idx])
nearest_region_idx = int(np.argmin(dmat[nearest_patch_local_idx]))

out = {
    "case_id": case,
    "local_region_name": "base_edge_or_hinge_region",
    "region_parts": region_parts,
    "center_hand_vertex": center_idx,
    "patch_radius": patch_radius,
    "num_patch_vertices": int(len(patch_ids)),
    "patch_min_distance": float(np.min(d)),
    "patch_p1_distance": float(np.percentile(d, 1)),
    "patch_p5_distance": float(np.percentile(d, 5)),
    "patch_mean_distance": float(np.mean(d)),
    "nearest_hand_vertex_in_patch": nearest_hand_idx,
    "nearest_hand_xyz": hand_points[nearest_hand_idx].tolist(),
    "nearest_region_vertex": nearest_region_idx,
    "nearest_region_xyz": region_points[nearest_region_idx].tolist(),
    **threshold_counts,
    **threshold_ratios,
    "interpretation_hint": "If several patch vertices are within 0.03-0.05, contact is more reliable than a single-vertex nearest point."
}

out_path.write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
