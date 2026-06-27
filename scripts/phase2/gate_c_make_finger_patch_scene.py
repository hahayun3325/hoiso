from pathlib import Path
import json
import numpy as np
import trimesh

case = "alapuse01"
root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases") / case

hand_path = root / "input/final_hand.ply"
part_dir = root / "part_meshes_partfield_v2_vmap"
patch_report = root / "gate_b_contact/metrics/gate_c_finger_patch_local_region_check.json"
out_dir = root / "gate_b_contact/visuals/gate_c_finger_patch_local_region"
out_scene = out_dir / "gate_c_finger_patch_local_region.glb"

out_dir.mkdir(parents=True, exist_ok=True)

report = json.loads(patch_report.read_text())

hand = trimesh.load(hand_path, force="mesh", process=False)
hand_points = np.asarray(hand.vertices)

scene = trimesh.Scene()
scene.add_geometry(hand, node_name="hand")

for name in ["keyboard_base", "hinge"]:
    p = part_dir / f"{name}.ply"
    if p.exists():
        scene.add_geometry(trimesh.load(p, force="mesh", process=False), node_name=name)

center_xyz = hand_points[int(report["center_hand_vertex"])]
patch_radius = float(report["patch_radius"])
patch_d = np.linalg.norm(hand_points - center_xyz[None, :], axis=1)
patch_ids = np.where(patch_d <= patch_radius)[0]

# Show local hand patch with small orange spheres.
for i, vid in enumerate(patch_ids):
    if i % 3 != 0:
        continue
    s = trimesh.creation.uv_sphere(radius=0.004)
    s.apply_translation(hand_points[vid])
    s.visual.vertex_colors = [255, 128, 0, 255]
    scene.add_geometry(s, node_name=f"patch_v_{int(vid)}")

# Nearest hand point and nearest region point.
h_xyz = np.asarray(report["nearest_hand_xyz"])
r_xyz = np.asarray(report["nearest_region_xyz"])

h_sphere = trimesh.creation.uv_sphere(radius=0.014)
h_sphere.apply_translation(h_xyz)
h_sphere.visual.vertex_colors = [255, 0, 0, 255]

r_sphere = trimesh.creation.uv_sphere(radius=0.012)
r_sphere.apply_translation(r_xyz)
r_sphere.visual.vertex_colors = [0, 255, 255, 255]

scene.add_geometry(h_sphere, node_name="nearest_patch_hand_red")
scene.add_geometry(r_sphere, node_name="nearest_region_cyan")

scene.export(out_scene)
print("[OK] wrote", out_scene)
