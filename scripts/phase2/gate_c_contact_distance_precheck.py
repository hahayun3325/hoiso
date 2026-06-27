from pathlib import Path
import json
import numpy as np
import trimesh

case = "alapuse01"
root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases") / case

hand_path = root / "input/final_hand.ply"
part_dir = root / "part_meshes_partfield_v2_vmap"
contact_json = root / "gate_b_contact/manual_json/alapuse01_contact_proposal_v1_manual.json"
out_path = root / "gate_b_contact/metrics/gate_c_contact_distance_precheck.json"

hand = trimesh.load(hand_path, force="mesh", process=False)
data = json.loads(contact_json.read_text())

hand_points = np.asarray(hand.vertices)
report = {
    "case_id": case,
    "hand_vertices": int(len(hand_points)),
    "checks": []
}

for c in data["contacts"]:
    part_name = c["object_part"]
    part_path = part_dir / f"{part_name}.ply"

    if not part_path.exists() or c["state"] == "no_contact":
        report["checks"].append({
            "contact": c,
            "part_path": str(part_path),
            "status": "skipped_no_contact_or_missing_part"
        })
        continue

    part = trimesh.load(part_path, force="mesh", process=False)
    part_points = np.asarray(part.vertices)

    # Simple nearest-vertex distance. Later replace with surface distance/fingertip labels.
    diff = hand_points[:, None, :] - part_points[None, :, :]
    d = np.linalg.norm(diff, axis=-1).min(axis=1)

    row = {
        "contact": c,
        "part_path": str(part_path),
        "part_vertices": int(len(part_points)),
        "min_hand_to_part_dist": float(np.min(d)),
        "p1_hand_to_part_dist": float(np.percentile(d, 1)),
        "p5_hand_to_part_dist": float(np.percentile(d, 5)),
        "mean_hand_to_part_dist": float(np.mean(d)),
        "note": "Uses all hand vertices, not finger-specific vertices yet."
    }
    report["checks"].append(row)

out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
