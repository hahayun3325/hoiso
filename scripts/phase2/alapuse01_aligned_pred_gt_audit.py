from pathlib import Path
import json
import numpy as np
import trimesh

src = Path("/home/fredcui/foho_phase0/inspection/arctic_phase017/paper_style_eval_selected_cases_surface/alapuse01/default")
out_dir = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01/gt_reference")

paths = {
    "aligned_pred_hand": src / "aligned_pred_hand.ply",
    "aligned_pred_object": src / "aligned_pred_object.ply",
    "gt_right_hand": src / "gt_right_hand_points.ply",
    "gt_object": src / "gt_object_mesh.ply",
}

def load_pts(p):
    m = trimesh.load(p, process=False)
    if hasattr(m, "vertices"):
        return np.asarray(m.vertices)
    pts = []
    for g in m.geometry.values():
        pts.append(np.asarray(g.vertices))
    return np.concatenate(pts, axis=0)

def bbox(pts):
    mn = pts.min(axis=0)
    mx = pts.max(axis=0)
    c = (mn + mx) / 2
    e = mx - mn
    return {
        "min": mn.tolist(),
        "max": mx.tolist(),
        "center": c.tolist(),
        "extent": e.tolist(),
        "diag": float(np.linalg.norm(e)),
        "num_points": int(len(pts)),
    }

def nn(a, b, chunk=512):
    out = []
    for i in range(0, len(a), chunk):
        aa = a[i:i+chunk]
        d = np.linalg.norm(aa[:, None, :] - b[None, :, :], axis=-1).min(axis=1)
        out.append(d)
    return np.concatenate(out)

pts = {k: load_pts(p) for k, p in paths.items()}

stats = {k: bbox(v) for k, v in pts.items()}

def center_dist(a, b):
    ca = np.asarray(stats[a]["center"])
    cb = np.asarray(stats[b]["center"])
    return float(np.linalg.norm(ca - cb))

hand_d = nn(pts["aligned_pred_hand"], pts["gt_right_hand"])
obj_d = nn(pts["aligned_pred_object"], pts["gt_object"])

report = {
    "case_id": "alapuse01",
    "source": str(src),
    "stats": stats,
    "center_distances": {
        "aligned_pred_hand_to_gt_right_hand": center_dist("aligned_pred_hand", "gt_right_hand"),
        "aligned_pred_object_to_gt_object": center_dist("aligned_pred_object", "gt_object"),
        "aligned_pred_hand_to_aligned_pred_object": center_dist("aligned_pred_hand", "aligned_pred_object"),
        "gt_right_hand_to_gt_object": center_dist("gt_right_hand", "gt_object"),
    },
    "nearest_neighbor": {
        "pred_hand_to_gt_hand_mean": float(np.mean(hand_d)),
        "pred_hand_to_gt_hand_p50": float(np.percentile(hand_d, 50)),
        "pred_hand_to_gt_hand_p95": float(np.percentile(hand_d, 95)),
        "pred_object_to_gt_object_mean": float(np.mean(obj_d)),
        "pred_object_to_gt_object_p50": float(np.percentile(obj_d, 50)),
        "pred_object_to_gt_object_p95": float(np.percentile(obj_d, 95)),
    },
    "decision_hint": "If aligned center distances are much smaller than raw audit, the earlier issue was coordinate-frame mismatch, not necessarily frame mismatch."
}

out = out_dir / "alapuse01_aligned_pred_gt_audit_v1.json"
out.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
print("[OK] wrote", out)
