from pathlib import Path
import json
import numpy as np
import trimesh

case = "alapuse01"
root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases") / case

hand_path = root / "input/final_hand.ply"
part_dir = root / "part_meshes_partfield_v2_vmap"
target_path = root / "gate_d_optimization/targets/gate_d_contact_target_dryrun_v1.json"

out_scene = root / "gate_d_optimization/visuals/gate_d_contact_target_dryrun_v1.glb"
out_scene.parent.mkdir(parents=True, exist_ok=True)

target = json.loads(target_path.read_text())

scene = trimesh.Scene()
scene.add_geometry(trimesh.load(hand_path, force="mesh", process=False), node_name="hand")

for name in ["keyboard_base", "hinge"]:
    p = part_dir / f"{name}.ply"
    if p.exists():
        scene.add_geometry(trimesh.load(p, force="mesh", process=False), node_name=name)

hand_xyz = np.asarray(target["nearest_hand_xyz"], dtype=float)
region_xyz = np.asarray(target["nearest_region_xyz"], dtype=float)

h = trimesh.creation.uv_sphere(radius=0.014)
h.apply_translation(hand_xyz)
h.visual.vertex_colors = [255, 0, 0, 255]

r = trimesh.creation.uv_sphere(radius=0.012)
r.apply_translation(region_xyz)
r.visual.vertex_colors = [0, 255, 255, 255]

scene.add_geometry(h, node_name="gate_d_hand_contact_target_red")
scene.add_geometry(r, node_name="gate_d_object_contact_target_cyan")

scene.export(out_scene)
print("[OK] wrote", out_scene)
