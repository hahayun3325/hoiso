from pathlib import Path
import json
import numpy as np
import trimesh

case_root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
gt_path = case_root / "gt_reference/selected/gt_object_mesh.ply"

candidates = {
    "phase2_current_singleblob": case_root / "input/final_object_singleblob.ply",
    "phase1_baseline": Path("/home/fredcui/foho_phase0/phase1_report_assets/meshes/alapuse01/baseline/final_object.ply"),
    "phase1_selector_gpt55": Path("/home/fredcui/foho_phase0/phase1_report_assets/meshes/alapuse01/selector_gpt55/final_object.ply"),
    "phase1_selector_v41": Path("/home/fredcui/foho_phase0/phase1_report_assets/meshes/alapuse01/selector_v41/final_object.ply"),
    "partaware_attempt0": Path("/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_alapuse01_partaware_v2/attempt0_partaware_prompt/run_outputs/arctic_alapuse01_partaware_v2_attempt0/foho_debug/20260620_191408_exp_objalapuse01_inpainted/final_obj_mesh.ply"),
}

def load_points(p):
    m = trimesh.load(p, force="mesh", process=False)
    pts = np.asarray(m.vertices)
    return m, pts

def nn_dist(a, b, chunk=512):
    out = []
    for i in range(0, len(a), chunk):
        aa = a[i:i+chunk]
        d = np.linalg.norm(aa[:, None, :] - b[None, :, :], axis=-1).min(axis=1)
        out.append(d)
    return np.concatenate(out)

gt_mesh, gt_pts = load_points(gt_path)

rows = []
for name, p in candidates.items():
    if not p.exists():
        rows.append({"name": name, "path": str(p), "exists": False})
        continue

    mesh, pts = load_points(p)
    pred_to_gt = nn_dist(pts, gt_pts)
    gt_to_pred = nn_dist(gt_pts, pts)

    comps = mesh.split(only_watertight=False)

    rows.append({
        "name": name,
        "path": str(p),
        "exists": True,
        "num_vertices": int(len(pts)),
        "num_faces": int(len(mesh.faces)),
        "num_components": int(len(comps)),
        "pred_to_gt_mean": float(np.mean(pred_to_gt)),
        "gt_to_pred_mean": float(np.mean(gt_to_pred)),
        "sym_mean_vertex_nn": float(0.5 * (np.mean(pred_to_gt) + np.mean(gt_to_pred))),
        "pred_to_gt_p5": float(np.percentile(pred_to_gt, 5)),
        "pred_to_gt_p50": float(np.percentile(pred_to_gt, 50)),
        "gt_to_pred_p50": float(np.percentile(gt_to_pred, 50)),
        "bounds": mesh.bounds.tolist()
    })

rows_sorted = sorted([r for r in rows if r.get("exists")], key=lambda x: x["sym_mean_vertex_nn"])

out = {
    "case_id": "alapuse01",
    "gt_object": str(gt_path),
    "note": "Vertex-nearest-neighbor diagnostic only. Use with visual inspection.",
    "ranking": rows_sorted,
    "missing": [r for r in rows if not r.get("exists")]
}

out_path = case_root / "gt_reference/alapuse01_object_seed_ranking_v1.json"
out_path.write_text(json.dumps(out, indent=2))

print(json.dumps(out, indent=2))
print("[OK] wrote", out_path)
