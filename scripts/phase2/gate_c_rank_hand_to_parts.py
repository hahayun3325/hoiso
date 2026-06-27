from pathlib import Path
import json
import numpy as np
import trimesh

case = "alapuse01"
root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases") / case

hand_path = root / "input/final_hand.ply"
part_dir = root / "part_meshes_partfield_v2_vmap"
out_json = root / "gate_b_contact/metrics/gate_c_hand_to_part_rank.json"
out_txt = root / "gate_b_contact/metrics/gate_c_hand_to_part_rank.txt"

hand = trimesh.load(hand_path, force="mesh", process=False)
hand_points = np.asarray(hand.vertices)

rows = []
for part_path in sorted(part_dir.glob("*.ply")):
    part_name = part_path.stem
    part = trimesh.load(part_path, force="mesh", process=False)
    part_points = np.asarray(part.vertices)

    diff = hand_points[:, None, :] - part_points[None, :, :]
    dmat = np.linalg.norm(diff, axis=-1)
    d = dmat.min(axis=1)

    nearest_hand_idx = int(np.argmin(d))
    nearest_part_idx = int(np.argmin(dmat[nearest_hand_idx]))

    rows.append({
        "part": part_name,
        "part_vertices": int(len(part_points)),
        "min": float(np.min(d)),
        "p1": float(np.percentile(d, 1)),
        "p5": float(np.percentile(d, 5)),
        "mean": float(np.mean(d)),
        "nearest_hand_vertex": nearest_hand_idx,
        "nearest_part_vertex": nearest_part_idx,
        "nearest_hand_xyz": hand_points[nearest_hand_idx].tolist(),
        "nearest_part_xyz": part_points[nearest_part_idx].tolist()
    })

rows = sorted(rows, key=lambda x: x["min"])

out_json.parent.mkdir(parents=True, exist_ok=True)
out_json.write_text(json.dumps(rows, indent=2))

lines = []
for r in rows:
    lines.append(
        f'{r["part"]:20s} min={r["min"]:.6f} p1={r["p1"]:.6f} p5={r["p5"]:.6f} mean={r["mean"]:.6f}'
    )
out_txt.write_text("\n".join(lines))
print("\n".join(lines))
print("[OK] wrote", out_json)
