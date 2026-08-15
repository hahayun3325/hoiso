from pathlib import Path
import json
import numpy as np
import trimesh

case_root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
eval_base = Path("/home/fredcui/foho_phase0/inspection/arctic_phase017/paper_style_eval_selected_cases_surface/alapuse01")

methods = {
    "default": {
        "hand": eval_base / "default/aligned_pred_hand.ply",
        "object": eval_base / "default/aligned_pred_object.ply",
    },
    "gpt55_selector": {
        "hand": eval_base / "gpt55_selector/aligned_pred_hand.ply",
        "object": eval_base / "gpt55_selector/aligned_pred_object.ply",
    },
    "selector_v41_diagnostic": {
        "hand": case_root / "gt_reference/selector_v41_aligned_diagnostic/aligned_pred_hand_selector_v41.ply",
        "object": case_root / "gt_reference/selector_v41_aligned_diagnostic/aligned_pred_object_selector_v41.ply",
    }
}

gt_hand = case_root / "gt_reference/selected/gt_right_hand_points.ply"
gt_object = case_root / "gt_reference/selected/gt_object_mesh.ply"

def pts(p):
    m = trimesh.load(p, process=False)
    if hasattr(m, "vertices"):
        return np.asarray(m.vertices)
    return np.concatenate([np.asarray(g.vertices) for g in m.geometry.values()], axis=0)

def bbox(x):
    mn, mx = x.min(axis=0), x.max(axis=0)
    return {
        "center": ((mn + mx) / 2).tolist(),
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

gt_h = pts(gt_hand)
gt_o = pts(gt_object)
bh_gt = bbox(gt_h)
bo_gt = bbox(gt_o)
gt_hand_obj_center = float(np.linalg.norm(np.array(bh_gt["center"]) - np.array(bo_gt["center"])))

rows = []
for name, d in methods.items():
    if not d["hand"].exists() or not d["object"].exists():
        rows.append({"method": name, "exists": False})
        continue

    ph = pts(d["hand"])
    po = pts(d["object"])
    bh = bbox(ph)
    bo = bbox(po)

    hand_nn = nn(ph, gt_h)
    obj_nn = nn(po, gt_o)

    rows.append({
        "method": name,
        "exists": True,
        "pred_hand_to_gt_hand_center": float(np.linalg.norm(np.array(bh["center"]) - np.array(bh_gt["center"]))),
        "pred_object_to_gt_object_center": float(np.linalg.norm(np.array(bo["center"]) - np.array(bo_gt["center"]))),
        "pred_hand_to_pred_object_center": float(np.linalg.norm(np.array(bh["center"]) - np.array(bo["center"]))),
        "gt_hand_to_gt_object_center": gt_hand_obj_center,
        "hand_object_center_abs_error": abs(float(np.linalg.norm(np.array(bh["center"]) - np.array(bo["center"]))) - gt_hand_obj_center),
        "pred_object_diag": bo["diag"],
        "gt_object_diag": bo_gt["diag"],
        "object_diag_abs_error": abs(bo["diag"] - bo_gt["diag"]),
        "pred_hand_to_gt_hand_nn_mean": float(hand_nn.mean()),
        "pred_object_to_gt_object_nn_mean": float(obj_nn.mean()),
        "pred_object_to_gt_object_nn_p50": float(np.percentile(obj_nn, 50)),
        "pred_object_to_gt_object_nn_p95": float(np.percentile(obj_nn, 95)),
        "hand_path": str(d["hand"]),
        "object_path": str(d["object"]),
    })

out = case_root / "gt_reference/alapuse01_all_aligned_methods_compare_v1.json"
out.write_text(json.dumps(rows, indent=2))
print(json.dumps(rows, indent=2))
print("[OK] wrote", out)
