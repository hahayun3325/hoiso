from pathlib import Path
import json

import numpy as np
import trimesh
from scipy.spatial import cKDTree


DATA = Path("/home/fredcui/foho_phase0")
TOKEN = "alapuse02v6n60"

RUN_ROOT = (
    DATA
    / "phase1_diagnostics/selector_v41_full_pipeline/runs"
    / f"arctic_{TOKEN}_selector_v41_refined_pipeline"
)
CASE_ROOT = (
    DATA
    / "phase2_gateA_part_recon/cases"
    / "alapuse02_v6_n60"
)
PART_DIR = CASE_ROOT / "part_meshes_partfield_n2_vmap"
EXP_DIR = CASE_ROOT / "gate_c_experiment"
OUT = CASE_ROOT / "gate_d_v0_5_two_stage_arthoi_informed/preflight"

OUT.mkdir(parents=True, exist_ok=True)

hand = trimesh.load(
    RUN_ROOT / f"guidance_out/{TOKEN}_hand.ply",
    force="mesh",
    process=False,
)
screen = trimesh.load(
    PART_DIR / "screen_lid.ply",
    force="mesh",
    process=False,
)
base = trimesh.load(
    PART_DIR / "keyboard_base.ply",
    force="mesh",
    process=False,
)

T = np.load(EXP_DIR / f"{TOKEN}_object_only_h2m.npy")
screen.apply_transform(T)
base.apply_transform(T)

screen_vertices = np.asarray(screen.vertices)

try:
    boundary_ids = np.unique(screen.edges_boundary.reshape(-1))
except Exception:
    boundary_ids = np.arange(len(screen_vertices))

if len(boundary_ids) < 10:
    boundary_ids = np.arange(len(screen_vertices))

base_tree = cKDTree(np.asarray(base.vertices))
distance_to_base, _ = base_tree.query(screen_vertices[boundary_ids])

patch_size = min(40, len(boundary_ids))
selected_order = np.argsort(distance_to_base)[-patch_size:]
patch_ids = boundary_ids[selected_order]
patch_points = screen_vertices[patch_ids]

np.save(OUT / "screen_outer_edge_patch_vertex_ids.npy", patch_ids)
np.save(OUT / "screen_outer_edge_patch_points.npy", patch_points)

hand.visual.vertex_colors = [240, 90, 90, 255]
screen.visual.vertex_colors = [80, 130, 255, 180]
base.visual.vertex_colors = [100, 230, 130, 180]

scene = trimesh.Scene([hand, screen, base])

for point in patch_points:
    marker = trimesh.creation.icosphere(subdivisions=1, radius=0.006)
    marker.apply_translation(point)
    marker.visual.vertex_colors = [255, 0, 255, 255]
    scene.add_geometry(marker)

scene_path = OUT / f"{TOKEN}_gate_d_v0_5_target_patch_preflight.glb"
scene.export(scene_path)

report = {
    "case": TOKEN,
    "patch_rule": (
        "screen boundary vertices farthest from keyboard_base"
    ),
    "patch_size": int(len(patch_ids)),
    "patch_vertex_ids": patch_ids.tolist(),
    "decision": "PENDING_VISUAL_REVIEW",
    "expected_location": (
        "outer/top screen edge touched by the upper right hand"
    ),
}

report_path = OUT / "target_patch_preflight.json"
report_path.write_text(json.dumps(report, indent=2) + "\n")

print("[OK] scene :", scene_path)
print("[OK] report:", report_path)
print("[REVIEW] magenta markers must lie on the intended outer lid edge")
