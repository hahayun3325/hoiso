from pathlib import Path
import json
import numpy as np
import trimesh

case = "alapuse01"
root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases") / case

opt_hand_path = root / "gate_d_optimization/selected_optimizer_v0_contact_only/hand_optimizer_v0_contact_only_selected.ply"
part_dir = root / "part_meshes_partfield_v2_vmap"
report_path = root / "gate_d_optimization/collision_precheck_v1/gate_d_collision_risk_precheck_v1.json"

out_scene = root / "gate_d_optimization/collision_precheck_v1/gate_d_collision_risk_scene_v1.glb"

report = json.loads(report_path.read_text())
risk_ids = report["new_very_close_vertices"]["vertex_ids"]

scene = trimesh.Scene()

hand = trimesh.load(opt_hand_path, force="mesh", process=False)
scene.add_geometry(hand, node_name="optimized_hand")

for name in ["screen", "keyboard_base", "hinge", "residual_uncertain"]:
    p = part_dir / f"{name}.ply"
    if p.exists():
        scene.add_geometry(trimesh.load(p, force="mesh", process=False), node_name=name)

hand_pts = np.asarray(hand.vertices)

# Red markers = vertices that became newly very close to the full object.
for vid in risk_ids[:80]:
    s = trimesh.creation.uv_sphere(radius=0.006)
    s.apply_translation(hand_pts[int(vid)])
    s.visual.vertex_colors = [255, 0, 0, 255]
    scene.add_geometry(s, node_name=f"new_very_close_hand_v_{int(vid)}")

out_scene.parent.mkdir(parents=True, exist_ok=True)
scene.export(out_scene)
print("[OK] wrote", out_scene)
