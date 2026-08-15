from pathlib import Path
import json
import numpy as np
import trimesh

case_root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")

paths = {
    "pred_hand_current": case_root / "input/final_hand.ply",
    "pred_object_current": case_root / "input/final_object_singleblob.ply",
    "gt_right_hand": case_root / "gt_reference/selected/gt_right_hand_points.ply",
    "gt_object": case_root / "gt_reference/selected/gt_object_mesh.ply",
    "phase1_baseline_hand": Path("/home/fredcui/foho_phase0/phase1_report_assets/meshes/alapuse01/baseline/final_hand.ply"),
    "phase1_selector_v41_hand": Path("/home/fredcui/foho_phase0/phase1_report_assets/meshes/alapuse01/selector_v41/final_hand.ply"),
}

def load_vertices(p):
    obj = trimesh.load(p, process=False)
    if hasattr(obj, "vertices"):
        return np.asarray(obj.vertices)
    if hasattr(obj, "geometry"):
        pts = []
        for g in obj.geometry.values():
            if hasattr(g, "vertices"):
                pts.append(np.asarray(g.vertices))
        return np.concatenate(pts, axis=0)
    raise RuntimeError(f"Cannot load vertices from {p}")

def stats(name, p):
    pts = load_vertices(p)
    bmin = pts.min(axis=0)
    bmax = pts.max(axis=0)
    center = (bmin + bmax) / 2
    extent = bmax - bmin
    return {
        "name": name,
        "path": str(p),
        "num_points": int(len(pts)),
        "bbox_min": bmin.tolist(),
        "bbox_max": bmax.tolist(),
        "bbox_center": center.tolist(),
        "bbox_extent": extent.tolist(),
        "bbox_diag": float(np.linalg.norm(extent)),
    }, pts

reports = {}
pts_cache = {}
for name, p in paths.items():
    if p.exists():
        r, pts = stats(name, p)
        reports[name] = r
        pts_cache[name] = pts
    else:
        reports[name] = {"name": name, "path": str(p), "exists": False}

def center_dist(a, b):
    ca = np.array(reports[a]["bbox_center"])
    cb = np.array(reports[b]["bbox_center"])
    return float(np.linalg.norm(ca - cb))

pairwise = {}
pairs = [
    ("pred_hand_current", "pred_object_current"),
    ("gt_right_hand", "gt_object"),
    ("pred_hand_current", "gt_right_hand"),
    ("pred_object_current", "gt_object"),
    ("phase1_baseline_hand", "gt_right_hand"),
    ("phase1_selector_v41_hand", "gt_right_hand"),
]
for a, b in pairs:
    if a in reports and b in reports and reports[a].get("exists", True) and reports[b].get("exists", True):
        pairwise[f"{a}__to__{b}_bbox_center_dist"] = center_dist(a, b)

out = {
    "case_id": "alapuse01",
    "note": "This is a coordinate-frame and alignment audit. Large pred-vs-GT center distance means raw files may not share a frame.",
    "items": reports,
    "pairwise_center_distances": pairwise,
    "interpretation_hint": {
        "if_pred_object_to_gt_object_is_large": "GT and prediction are likely not in the same coordinate frame, or object alignment is wrong.",
        "if_pred_hand_to_gt_right_hand_is_large": "right-hand placement is wrong or hand source/transform is wrong.",
        "if_pred_hand_to_object_differs_from_gt_hand_to_object": "hand-object relative alignment is wrong."
    }
}

out_path = case_root / "gt_reference/alapuse01_alignment_audit_v1.json"
out_path.write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
print("[OK] wrote", out_path)
