from pathlib import Path
import json
import numpy as np
import trimesh

case = "alapuse01"
root = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases") / case

rank_json = root / "gate_b_contact/metrics/gate_c_hand_to_part_rank.json"
hand_path = root / "input/final_hand.ply"
part_dir = root / "part_meshes_partfield_v2_vmap"
out_dir = root / "gate_b_contact/visuals/gate_c_nearest_markers_labeled"
out_scene = out_dir / "gate_c_nearest_markers_labeled.glb"
out_legend = out_dir / "gate_c_nearest_marker_legend.json"

out_dir.mkdir(parents=True, exist_ok=True)

rows = json.loads(rank_json.read_text())
hand = trimesh.load(hand_path, force="mesh", process=False)

scene = trimesh.Scene()
scene.add_geometry(hand, node_name="hand")

# Add object parts.
for part_path in sorted(part_dir.glob("*.ply")):
    scene.add_geometry(trimesh.load(part_path, force="mesh", process=False), node_name=part_path.stem)

colors = {
    "screen": [255, 0, 0, 255],
    "residual_uncertain": [255, 255, 0, 255],
    "hinge": [0, 255, 0, 255],
    "keyboard_base": [0, 128, 255, 255],
}

legend = []

for r in rows:
    part = r["part"]
    color = colors.get(part, [255, 255, 255, 255])

    h_xyz = np.asarray(r["nearest_hand_xyz"])
    p_xyz = np.asarray(r["nearest_part_xyz"])

    h_sphere = trimesh.creation.uv_sphere(radius=0.012)
    h_sphere.apply_translation(h_xyz)
    h_sphere.visual.vertex_colors = color

    p_sphere = trimesh.creation.uv_sphere(radius=0.008)
    p_sphere.apply_translation(p_xyz)
    p_sphere.visual.vertex_colors = color

    scene.add_geometry(h_sphere, node_name=f"{part}_nearest_HAND_marker")
    scene.add_geometry(p_sphere, node_name=f"{part}_nearest_PART_marker")

    legend.append({
        "part": part,
        "marker_color_rgba": color,
        "distance_min": r["min"],
        "distance_p1": r["p1"],
        "distance_p5": r["p5"],
        "nearest_hand_vertex": r["nearest_hand_vertex"],
        "nearest_hand_xyz": r["nearest_hand_xyz"],
        "nearest_part_vertex": r["nearest_part_vertex"],
        "nearest_part_xyz": r["nearest_part_xyz"]
    })

scene.export(out_scene)
out_legend.write_text(json.dumps(legend, indent=2))

print("[OK] wrote", out_scene)
print("[OK] wrote", out_legend)
print(json.dumps(legend, indent=2))
