from pathlib import Path
import trimesh

case_root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
out_dir = case_root / "gt_reference/visuals_alignment_audit"
out_dir.mkdir(parents=True, exist_ok=True)

items = {
    "pred_hand_current": case_root / "input/final_hand.ply",
    "pred_object_current": case_root / "input/final_object_singleblob.ply",
    "gt_right_hand": case_root / "gt_reference/selected/gt_right_hand_points.ply",
    "gt_object": case_root / "gt_reference/selected/gt_object_mesh.ply",
    "phase1_baseline_hand": Path("/home/fredcui/foho_phase0/phase1_report_assets/meshes/alapuse01/baseline/final_hand.ply"),
    "phase1_selector_v41_hand": Path("/home/fredcui/foho_phase0/phase1_report_assets/meshes/alapuse01/selector_v41/final_hand.ply"),
}

scene = trimesh.Scene()
for name, p in items.items():
    if p.exists():
        scene.add_geometry(trimesh.load(p, force="mesh", process=False), node_name=name)
    else:
        print("[MISS]", name, p)

out = out_dir / "alapuse01_pred_gt_hand_object_alignment_audit_raw.glb"
scene.export(out)
print("[OK] wrote", out)
