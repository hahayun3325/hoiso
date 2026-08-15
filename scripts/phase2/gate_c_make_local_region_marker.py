from pathlib import Path
import json
import numpy as np
import trimesh

case = "alapuse01"
root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases") / case

hand_path = root / "input/final_hand.ply"
part_dir = root / "part_meshes_partfield_v2_vmap"
report_path = root / "gate_b_contact/metrics/gate_c_local_contact_region_precheck.json"
out_dir = root / "gate_b_contact/visuals/gate_c_local_region_marker"
out_scene = out_dir / "gate_c_local_region_marker.glb"

out_dir.mkdir(parents=True, exist_ok=True)

report = json.loads(report_path.read_text())

scene = trimesh.Scene()
scene.add_geometry(trimesh.load(hand_path, force="mesh", process=False), node_name="hand")

for name in ["keyboard_base", "hinge"]:
    p = part_dir / f"{name}.ply"
    if p.exists():
        scene.add_geometry(trimesh.load(p, force="mesh", process=False), node_name=name)

h_xyz = np.asarray(report["nearest_hand_xyz"])
p_xyz = np.asarray(report["nearest_region_xyz"])

h_sphere = trimesh.creation.uv_sphere(radius=0.012)
h_sphere.apply_translation(h_xyz)
h_sphere.visual.vertex_colors = [255, 128, 0, 255]

p_sphere = trimesh.creation.uv_sphere(radius=0.010)
p_sphere.apply_translation(p_xyz)
p_sphere.visual.vertex_colors = [0, 255, 255, 255]

scene.add_geometry(h_sphere, node_name="nearest_hand_to_base_edge_region_orange")
scene.add_geometry(p_sphere, node_name="nearest_base_edge_region_point_cyan")

scene.export(out_scene)
print("[OK] wrote", out_scene)
