from pathlib import Path
import trimesh

case_root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
src = case_root / "gt_reference/selector_v41_aligned_diagnostic"
out_dir = case_root / "gt_reference/visuals_alignment_audit"
out_dir.mkdir(parents=True, exist_ok=True)

items = {
    "selector_v41_aligned_hand": src / "aligned_pred_hand_selector_v41.ply",
    "selector_v41_aligned_object": src / "aligned_pred_object_selector_v41.ply",
    "gt_right_hand": case_root / "gt_reference/selected/gt_right_hand_points.ply",
    "gt_object": case_root / "gt_reference/selected/gt_object_mesh.ply",
}

scene = trimesh.Scene()
for name, p in items.items():
    if p.exists():
        scene.add_geometry(trimesh.load(p, force="mesh", process=False), node_name=name)
        print("[OK]", name, p)
    else:
        print("[MISS]", name, p)

out = out_dir / "alapuse01_selector_v41_aligned_pred_vs_gt.glb"
scene.export(out)
print("[OK] wrote", out)
