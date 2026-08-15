from pathlib import Path
import json
import numpy as np
import trimesh

base = Path("/home/fredcui/foho_phase0/inspection/arctic_phase017/paper_style_eval_selected_cases_surface/alapuse01")
out_dir = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01/gt_reference")
methods = ["default", "gpt55_selector"]

def pts(p):
    m = trimesh.load(p, process=False)
    if hasattr(m, "vertices"):
        return np.asarray(m.vertices)
    return np.concatenate([np.asarray(g.vertices) for g in m.geometry.values()], axis=0)

def bbox(x):
    mn, mx = x.min(axis=0), x.max(axis=0)
    return {
        "center": ((mn + mx) / 2).tolist(),
        "extent": (mx - mn).tolist(),
        "diag": float(np.linalg.norm(mx - mn)),
        "num": int(len(x)),
    }

def nn(a, b, chunk=512):
    out = []
    for i in range(0, len(a), chunk):
        aa = a[i:i+chunk]
        d = np.linalg.norm(aa[:, None, :] - b[None, :, :], axis=-1).min(axis=1)
        out.append(d)
    return np.concatenate(out)

rows = []
for method in methods:
    src = base / method
    pred_h = pts(src / "aligned_pred_hand.ply")
    pred_o = pts(src / "aligned_pred_object.ply")
    gt_h = pts(src / "gt_right_hand_points.ply")
    gt_o = pts(src / "gt_object_mesh.ply")

    bh, bo, gh, go = bbox(pred_h), bbox(pred_o), bbox(gt_h), bbox(gt_o)

    row = {
        "method": method,
        "pred_hand_to_gt_hand_center": float(np.linalg.norm(np.array(bh["center"]) - np.array(gh["center"]))),
        "pred_object_to_gt_object_center": float(np.linalg.norm(np.array(bo["center"]) - np.array(go["center"]))),
        "pred_hand_to_pred_object_center": float(np.linalg.norm(np.array(bh["center"]) - np.array(bo["center"]))),
        "gt_hand_to_gt_object_center": float(np.linalg.norm(np.array(gh["center"]) - np.array(go["center"]))),
        "pred_object_diag": bo["diag"],
        "gt_object_diag": go["diag"],
        "pred_hand_to_gt_hand_nn_mean": float(nn(pred_h, gt_h).mean()),
        "pred_object_to_gt_object_nn_mean": float(nn(pred_o, gt_o).mean()),
    }
    rows.append(row)

out = out_dir / "alapuse01_default_vs_gpt55_aligned_compare_v1.json"
out.write_text(json.dumps(rows, indent=2))
print(json.dumps(rows, indent=2))
print("[OK] wrote", out)
