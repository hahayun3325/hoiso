from pathlib import Path
import trimesh

case_root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
out_dir = case_root / "gt_reference/visuals"
out_dir.mkdir(parents=True, exist_ok=True)

items = {
    "gt_object": case_root / "gt_reference/selected/gt_object_mesh.ply",
    "gt_right_hand": case_root / "gt_reference/selected/gt_right_hand_points.ply",
    "phase1_baseline_object": Path("/home/fredcui/foho_phase0/phase1_report_assets/meshes/alapuse01/baseline/final_object.ply"),
    "phase1_selector_gpt55_object": Path("/home/fredcui/foho_phase0/phase1_report_assets/meshes/alapuse01/selector_gpt55/final_object.ply"),
    "phase1_selector_v41_object": Path("/home/fredcui/foho_phase0/phase1_report_assets/meshes/alapuse01/selector_v41/final_object.ply"),
    "current_phase2_object": case_root / "input/final_object_singleblob.ply",
}

for name, p in items.items():
    if not p.exists():
        print("[MISS]", name, p)

# Make one scene per candidate to avoid visual clutter.
for cand_name in ["phase1_baseline_object", "phase1_selector_gpt55_object", "phase1_selector_v41_object", "current_phase2_object"]:
    scene = trimesh.Scene()

    for name in ["gt_object", "gt_right_hand", cand_name]:
        p = items[name]
        if p.exists():
            scene.add_geometry(trimesh.load(p, force="mesh", process=False), node_name=name)

    out = out_dir / f"gt_compare_{cand_name}.glb"
    scene.export(out)
    print("[OK] wrote", out)
