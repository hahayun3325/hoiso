from pathlib import Path
import argparse
import json
import numpy as np
import trimesh

ap = argparse.ArgumentParser()
ap.add_argument("--case-root", required=True)
ap.add_argument("--opt-hand", required=True)
ap.add_argument("--tag", required=True)
args = ap.parse_args()

root = Path(args.case_root)
orig_hand_path = root / "input/final_hand.ply"
opt_hand_path = Path(args.opt_hand)
part_dir = root / "part_meshes_partfield_v2_vmap"

out_dir = root / "gate_d_optimization" / f"collision_precheck_{args.tag}"
out_metrics = out_dir / f"gate_d_collision_risk_precheck_{args.tag}.json"
out_dir.mkdir(parents=True, exist_ok=True)

object_part_names = ["screen", "keyboard_base", "hinge", "residual_uncertain"]

def load_points(path):
    m = trimesh.load(path, force="mesh", process=False)
    return m, np.asarray(m.vertices)

def concat_points(names):
    meshes = []
    for name in names:
        p = part_dir / f"{name}.ply"
        if p.exists():
            meshes.append(trimesh.load(p, force="mesh", process=False))
    m = trimesh.util.concatenate(meshes)
    return m, np.asarray(m.vertices)

def nearest_distances(q, t, chunk=256):
    out = []
    for i in range(0, len(q), chunk):
        qq = q[i:i+chunk]
        d = np.linalg.norm(qq[:, None, :] - t[None, :, :], axis=-1).min(axis=1)
        out.append(d)
    return np.concatenate(out)

def summary(d):
    row = {
        "min": float(np.min(d)),
        "p1": float(np.percentile(d, 1)),
        "p5": float(np.percentile(d, 5)),
        "mean": float(np.mean(d)),
    }
    for th in [0.003, 0.005, 0.010, 0.020, 0.030, 0.050]:
        row[f"num_within_{th:.3f}"] = int(np.sum(d <= th))
        row[f"ratio_within_{th:.3f}"] = float(np.mean(d <= th))
    return row

_, orig = load_points(orig_hand_path)
_, opt = load_points(opt_hand_path)
_, obj = concat_points(object_part_names)

orig_d = nearest_distances(orig, obj)
opt_d = nearest_distances(opt, obj)

risk_th = 0.005
new_ids = np.where((opt_d <= risk_th) & (orig_d > risk_th))[0]
shift = np.linalg.norm(opt - orig, axis=1)

report = {
    "tag": args.tag,
    "original_hand": str(orig_hand_path),
    "optimized_hand": str(opt_hand_path),
    "full_object_original": summary(orig_d),
    "full_object_optimized": summary(opt_d),
    "new_very_close_vertices": {
        "threshold": risk_th,
        "count": int(len(new_ids)),
        "ratio": float(len(new_ids) / len(opt)),
        "vertex_ids": new_ids[:200].astype(int).tolist()
    },
    "global_shift": {
        "mean": float(np.mean(shift)),
        "max": float(np.max(shift))
    }
}

out_metrics.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
print("[OK] wrote", out_metrics)
