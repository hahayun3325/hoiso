from pathlib import Path
import json
import numpy as np
import trimesh

case = "alapuse01"
root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases") / case

rank_json = root / "gate_b_contact/metrics/gate_c_hand_to_part_rank.json"
hand_path = root / "input/final_hand.ply"
part_dir = root / "part_meshes_partfield_v2_vmap"
out_dir = root / "gate_b_contact/visuals/gate_c_nearest_markers"
out_scene = out_dir / "gate_c_nearest_markers.glb"

out_dir.mkdir(parents=True, exist_ok=True)

rows = json.loads(rank_json.read_text())
hand = trimesh.load(hand_path, force="mesh", process=False)

scene = trimesh.Scene()
scene.add_geometry(hand, node_name="hand")

# Add all object parts.
for part_path in sorted(part_dir.glob("*.ply")):
    scene.add_geometry(trimesh.load(part_path, force="mesh", process=False), node_name=part_path.stem)

# Add small spheres for nearest hand/part vertices.
for r in rows:
    part = r["part"]
    h_xyz = np.asarray(r["nearest_hand_xyz"])
    p_xyz = np.asarray(r["nearest_part_xyz"])

    h_sphere = trimesh.creation.uv_sphere(radius=0.01)
    h_sphere.apply_translation(h_xyz)
    h_sphere.visual.vertex_colors = [255, 0, 0, 255]

    p_sphere = trimesh.creation.uv_sphere(radius=0.01)
    p_sphere.apply_translation(p_xyz)
    p_sphere.visual.vertex_colors = [0, 255, 0, 255]

    scene.add_geometry(h_sphere, node_name=f"{part}_nearest_hand_red")
    scene.add_geometry(p_sphere, node_name=f"{part}_nearest_part_green")

scene.export(out_scene)
print("[OK] wrote", out_scene)
