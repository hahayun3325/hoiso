from pathlib import Path
import trimesh

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
OUT = CASE_ROOT / "gate_d0_object_repair" / "visuals_clean"
OUT.mkdir(parents=True, exist_ok=True)

paths = {
    "original_object": CASE_ROOT / "part_meshes_partfield_v2_vmap/part_scene.glb",
    "pred_hand": CASE_ROOT / "input/final_hand.ply",
    "repaired_object": CASE_ROOT / "gate_d0_object_repair/outputs/object_repaired_oracle_similarity_to_gt.ply",
    "gt_object": CASE_ROOT / "gt_reference/selected/gt_object_mesh.ply",
    "gt_right_hand": CASE_ROOT / "gt_reference/selected/gt_right_hand_points.ply",
}

def load_any(path):
    obj = trimesh.load(path, force=None)
    if isinstance(obj, trimesh.Scene):
        geoms = list(obj.geometry.values())
        if not geoms:
            raise ValueError(f"empty scene: {path}")
        return trimesh.util.concatenate([g for g in geoms if hasattr(g, "vertices")])
    return obj

def colorize(obj, rgba):
    if hasattr(obj, "visual") and hasattr(obj, "vertices"):
        obj.visual.vertex_colors = rgba
    return obj

# Scene A: original frame
scene_a = trimesh.Scene()
orig = colorize(load_any(paths["original_object"]), [0, 0, 255, 120])
hand = colorize(load_any(paths["pred_hand"]), [0, 255, 0, 180])
scene_a.add_geometry(orig, node_name="original_pred_object_blue")
scene_a.add_geometry(hand, node_name="pred_hand_green")
scene_a.export(OUT / "scene_A_original_pred_object_and_hand.glb")

# Scene B: GT / oracle-repaired frame
scene_b = trimesh.Scene()
repaired = colorize(load_any(paths["repaired_object"]), [0, 0, 255, 170])
gt_obj = colorize(load_any(paths["gt_object"]), [180, 180, 180, 120])
scene_b.add_geometry(gt_obj, node_name="gt_object_gray")
scene_b.add_geometry(repaired, node_name="oracle_repaired_object_blue")

if paths["gt_right_hand"].exists():
    gt_hand = colorize(load_any(paths["gt_right_hand"]), [0, 255, 0, 180])
    scene_b.add_geometry(gt_hand, node_name="gt_right_hand_green")

scene_b.export(OUT / "scene_B_oracle_repaired_object_vs_gt_frame.glb")

print("[OK] wrote", OUT / "scene_A_original_pred_object_and_hand.glb")
print("[OK] wrote", OUT / "scene_B_oracle_repaired_object_vs_gt_frame.glb")
