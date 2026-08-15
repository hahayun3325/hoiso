from pathlib import Path
import json
import numpy as np
import trimesh

case_root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")

src_pred_hand = Path("/home/fredcui/foho_phase0/phase1_report_assets/meshes/alapuse01/selector_v41/final_hand.ply")
src_pred_object = Path("/home/fredcui/foho_phase0/phase1_report_assets/meshes/alapuse01/selector_v41/final_object.ply")

gt_hand = case_root / "gt_reference/selected/gt_right_hand_points.ply"
gt_object = case_root / "gt_reference/selected/gt_object_mesh.ply"

out_dir = case_root / "gt_reference/selector_v41_aligned_diagnostic"
out_dir.mkdir(parents=True, exist_ok=True)

def load_any(path):
    return trimesh.load(path, process=False)

def load_vertices(path):
    obj = load_any(path)

    if hasattr(obj, "vertices"):
        v = np.asarray(obj.vertices, dtype=np.float64)
        if len(v) > 0:
            return v

    if hasattr(obj, "geometry"):
        verts = []
        for g in obj.geometry.values():
            if hasattr(g, "vertices"):
                vv = np.asarray(g.vertices, dtype=np.float64)
                if len(vv) > 0:
                    verts.append(vv)
        if verts:
            return np.concatenate(verts, axis=0)

    raise RuntimeError(f"No vertices found in {path}; loaded type={type(obj)}")

def load_mesh_for_export(path):
    return trimesh.load(path, force="mesh", process=False)

def umeyama_similarity(src, dst, with_scale=True):
    assert len(src) > 0 and len(dst) > 0
    assert src.shape == dst.shape, f"shape mismatch: src={src.shape}, dst={dst.shape}"

    mu_src = src.mean(axis=0)
    mu_dst = dst.mean(axis=0)

    src_c = src - mu_src
    dst_c = dst - mu_dst

    cov = (dst_c.T @ src_c) / src.shape[0]
    U, S, Vt = np.linalg.svd(cov)

    D = np.eye(3)
    if np.linalg.det(U @ Vt) < 0:
        D[-1, -1] = -1

    R = U @ D @ Vt

    if with_scale:
        var_src = np.mean(np.sum(src_c ** 2, axis=1))
        scale = float(np.trace(np.diag(S) @ D) / var_src)
    else:
        scale = 1.0

    t = mu_dst - scale * (R @ mu_src)
    return scale, R, t

def apply_transform(mesh, scale, R, t):
    m = mesh.copy()
    v = np.asarray(m.vertices, dtype=np.float64)
    m.vertices = (scale * (R @ v.T)).T + t
    return m

pred_h_vertices = load_vertices(src_pred_hand)
gt_h_vertices = load_vertices(gt_hand)

print("[INFO] pred hand vertices:", pred_h_vertices.shape)
print("[INFO] gt hand vertices:", gt_h_vertices.shape)

if pred_h_vertices.shape != gt_h_vertices.shape:
    raise RuntimeError(
        f"Hand vertex count mismatch after robust loading: "
        f"pred={pred_h_vertices.shape}, gt={gt_h_vertices.shape}. "
        f"Need ICP fallback or official evaluation script."
    )

scale, R, t = umeyama_similarity(pred_h_vertices, gt_h_vertices, with_scale=True)

pred_h_mesh = load_mesh_for_export(src_pred_hand)
pred_o_mesh = load_mesh_for_export(src_pred_object)

aligned_h = apply_transform(pred_h_mesh, scale, R, t)
aligned_o = apply_transform(pred_o_mesh, scale, R, t)

out_h = out_dir / "aligned_pred_hand_selector_v41.ply"
out_o = out_dir / "aligned_pred_object_selector_v41.ply"

aligned_h.export(out_h)
aligned_o.export(out_o)

report = {
    "case_id": "alapuse01",
    "method": "selector_v41",
    "alignment": "hand_based_umeyama_similarity_v2_robust_pointcloud_loader",
    "source_pred_hand": str(src_pred_hand),
    "source_pred_object": str(src_pred_object),
    "target_gt_hand": str(gt_hand),
    "target_gt_object": str(gt_object),
    "output_aligned_hand": str(out_h),
    "output_aligned_object": str(out_o),
    "pred_hand_vertices": int(len(pred_h_vertices)),
    "gt_hand_vertices": int(len(gt_h_vertices)),
    "scale": scale,
    "rotation": R.tolist(),
    "translation": t.tolist(),
    "note": "Diagnostic selector-v41 alignment. Prefer official evaluator for final paper metrics."
}

out_json = out_dir / "selector_v41_alignment_transform_diagnostic_v2.json"
out_json.write_text(json.dumps(report, indent=2))

print(json.dumps(report, indent=2))
print("[OK] wrote", out_h)
print("[OK] wrote", out_o)
print("[OK] wrote", out_json)
