from pathlib import Path
import trimesh

case_root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
out_dir = case_root / "gt_reference/visuals_alignment_audit"
out_dir.mkdir(parents=True, exist_ok=True)

src = Path("/home/fredcui/foho_phase0/inspection/arctic_phase017/paper_style_eval_selected_cases_surface/alapuse01/default")

items = {
    "aligned_pred_hand": src / "aligned_pred_hand.ply",
    "aligned_pred_object": src / "aligned_pred_object.ply",
    "gt_right_hand": src / "gt_right_hand_points.ply",
    "gt_object": src / "gt_object_mesh.ply",
}

scene = trimesh.Scene()
for name, p in items.items():
    if p.exists():
        scene.add_geometry(trimesh.load(p, force="mesh", process=False), node_name=name)
        print("[OK]", name, p)
    else:
        print("[MISS]", name, p)

out = out_dir / "alapuse01_default_aligned_pred_vs_gt.glb"
scene.export(out)
print("[OK] wrote", out)
