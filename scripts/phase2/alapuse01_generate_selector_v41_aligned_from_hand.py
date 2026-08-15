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

def load_mesh(path):
    return trimesh.load(path, force="mesh", process=False)

def verts(mesh):
    return np.asarray(mesh.vertices).astype(np.float64)

def umeyama_similarity(src, dst, with_scale=True):
    """
    Find similarity transform mapping src -> dst.
    src, dst: Nx3 with corresponding points.
    Returns scale, rotation, translation.
    """
    assert src.shape == dst.shape, f"shape mismatch: {src.shape} vs {dst.shape}"

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

def apply_transform_mesh(mesh, scale, R, t):
    m = mesh.copy()
    v = verts(m)
    m.vertices = (scale * (R @ v.T)).T + t
    return m

pred_h_mesh = load_mesh(src_pred_hand)
pred_o_mesh = load_mesh(src_pred_object)
gt_h_mesh = load_mesh(gt_hand)

pred_h = verts(pred_h_mesh)
target_h = verts(gt_h_mesh)

if len(pred_h) != len(target_h):
    raise RuntimeError(f"Hand vertex count mismatch: pred={len(pred_h)}, gt={len(target_h)}. Need ICP fallback.")

scale, R, t = umeyama_similarity(pred_h, target_h, with_scale=True)

aligned_h = apply_transform_mesh(pred_h_mesh, scale, R, t)
aligned_o = apply_transform_mesh(pred_o_mesh, scale, R, t)

out_h = out_dir / "aligned_pred_hand_selector_v41.ply"
out_o = out_dir / "aligned_pred_object_selector_v41.ply"
out_h.export(out_h)
out_o.export(out_o)

report = {
    "case_id": "alapuse01",
    "method": "selector_v41",
    "alignment": "hand_based_umeyama_similarity",
    "source_pred_hand": str(src_pred_hand),
    "source_pred_object": str(src_pred_object),
    "target_gt_hand": str(gt_hand),
    "target_gt_object": str(gt_object),
    "output_aligned_hand": str(out_h),
    "output_aligned_object": str(out_o),
    "scale": scale,
    "rotation": R.tolist(),
    "translation": t.tolist(),
    "note": "Diagnostic alignment. Prefer official evaluation script if available."
}

out_json = out_dir / "selector_v41_alignment_transform_diagnostic.json"
out_json.write_text(json.dumps(report, indent=2))

print(json.dumps(report, indent=2))
print("[OK] wrote", out_h)
print("[OK] wrote", out_o)
print("[OK] wrote", out_json)
