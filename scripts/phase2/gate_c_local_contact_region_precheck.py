from pathlib import Path
import json
import numpy as np
import trimesh

case = "alapuse01"
root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases") / case

hand_path = root / "input/final_hand.ply"
part_dir = root / "part_meshes_partfield_v2_vmap"
out_path = root / "gate_b_contact/metrics/gate_c_local_contact_region_precheck.json"

hand = trimesh.load(hand_path, force="mesh", process=False)
hand_points = np.asarray(hand.vertices)

region_parts = ["keyboard_base", "hinge"]
meshes = []
for name in region_parts:
    p = part_dir / f"{name}.ply"
    if p.exists():
        meshes.append(trimesh.load(p, force="mesh", process=False))

region = trimesh.util.concatenate(meshes)
region_points = np.asarray(region.vertices)

diff = hand_points[:, None, :] - region_points[None, :, :]
dmat = np.linalg.norm(diff, axis=-1)
d = dmat.min(axis=1)

nearest_hand_idx = int(np.argmin(d))
nearest_region_idx = int(np.argmin(dmat[nearest_hand_idx]))

report = {
    "case_id": case,
    "local_region_name": "base_edge_or_hinge_region",
    "region_parts": region_parts,
    "hand_vertices": int(len(hand_points)),
    "region_vertices": int(len(region_points)),
    "min_hand_to_region_dist": float(np.min(d)),
    "p1_hand_to_region_dist": float(np.percentile(d, 1)),
    "p5_hand_to_region_dist": float(np.percentile(d, 5)),
    "mean_hand_to_region_dist": float(np.mean(d)),
    "nearest_hand_vertex": nearest_hand_idx,
    "nearest_hand_xyz": hand_points[nearest_hand_idx].tolist(),
    "nearest_region_vertex": nearest_region_idx,
    "nearest_region_xyz": region_points[nearest_region_idx].tolist(),
    "note": "Temporary local union of keyboard_base + hinge to handle noisy part labels near contact."
}

out_path.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
