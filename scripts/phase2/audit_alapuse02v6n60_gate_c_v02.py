from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import trimesh
from trimesh.proximity import closest_point


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
OUT = (
    CASE_ROOT
    / "integrated_gates/gate_c_v0_2_robust_audit"
)

HAND_PATH = RUN_ROOT / f"guidance_out/{TOKEN}_hand.ply"
T_PATH = CASE_ROOT / f"gate_c_experiment/{TOKEN}_object_only_h2m.npy"
WHOLE_PATH = (
    CASE_ROOT
    / "gate_a_early/bounded_preflight_v2/outputs/object_only_hunyuan"
    / f"{TOKEN}.png_hoi_mesh.ply"
)

FINGERTIP_NAMES = ["thumb", "index", "middle", "ring", "pinky"]
FINGERTIP_IDX = np.asarray([744, 320, 443, 554, 671], dtype=np.int64)


def load_mesh(path: Path) -> trimesh.Trimesh:
    if not path.is_file():
        raise FileNotFoundError(path)

    obj = trimesh.load(path, process=False)

    if isinstance(obj, trimesh.Scene):
        meshes = [
            geometry
            for geometry in obj.geometry.values()
            if isinstance(geometry, trimesh.Trimesh)
        ]
        if not meshes:
            raise RuntimeError(f"No mesh geometry in {path}")
        return trimesh.util.concatenate(meshes)

    if not isinstance(obj, trimesh.Trimesh):
        raise TypeError(f"Unsupported object from {path}: {type(obj)}")

    return obj


def surface_distances(
    mesh: trimesh.Trimesh,
    points: np.ndarray,
) -> np.ndarray:
    _, distance, _ = closest_point(mesh, points)
    return np.asarray(distance)


def marker(point: np.ndarray, rgba: list[int]) -> trimesh.Trimesh:
    sphere = trimesh.creation.icosphere(subdivisions=1, radius=0.006)
    sphere.apply_translation(point)
    sphere.visual.vertex_colors = rgba
    return sphere


OUT.joinpath("metrics").mkdir(parents=True, exist_ok=True)
OUT.joinpath("visuals").mkdir(parents=True, exist_ok=True)

T = np.load(T_PATH)

hand = load_mesh(HAND_PATH)
screen = load_mesh(PART_DIR / "screen_lid.ply")
base = load_mesh(PART_DIR / "keyboard_base.ply")
whole = load_mesh(WHOLE_PATH)

screen.apply_transform(T)
base.apply_transform(T)
whole.apply_transform(T)

if len(hand.vertices) <= int(FINGERTIP_IDX.max()):
    raise RuntimeError(
        f"Hand has only {len(hand.vertices)} vertices; "
        "the configured MANO fingertip indices are invalid."
    )

if not whole.is_watertight:
    raise RuntimeError(
        "The complete clean object mesh is not watertight. "
        "Do not run containment-based collision auditing."
    )

hand_vertices = np.asarray(hand.vertices)
fingertips = hand_vertices[FINGERTIP_IDX]

part_results = {}
patch_indices = {}

for name, mesh in {
    "screen_lid": screen,
    "keyboard_base": base,
}.items():
    all_distance = surface_distances(mesh, hand_vertices)
    fingertip_distance = surface_distances(mesh, fingertips)

    nearest_30 = np.argsort(all_distance)[:30]
    patch_indices[name] = nearest_30.tolist()

    part_results[name] = {
        "all_hand_min_cm": float(all_distance.min() * 100.0),
        "all_hand_p01_cm": float(np.quantile(all_distance, 0.01) * 100.0),
        "all_hand_p05_cm": float(np.quantile(all_distance, 0.05) * 100.0),
        "nearest_30_mean_cm": float(
            all_distance[nearest_30].mean() * 100.0
        ),
        "fingertip_cm": {
            finger: float(distance * 100.0)
            for finger, distance in zip(
                FINGERTIP_NAMES,
                fingertip_distance,
            )
        },
        "fingertip_min_cm": float(fingertip_distance.min() * 100.0),
        "fingertip_mean_cm": float(fingertip_distance.mean() * 100.0),
        "nearest_30_vertex_indices": nearest_30.tolist(),
    }

# Robust collision test:
# containment comes from the complete watertight object;
# penetration depth is approximated by unsigned distance to its surface.
inside = whole.contains(hand_vertices)
whole_surface_distance = surface_distances(whole, hand_vertices)
inside_depth = whole_surface_distance[inside]

collision = {
    "whole_object_watertight": bool(whole.is_watertight),
    "hand_vertices": int(len(hand_vertices)),
    "inside_count": int(inside.sum()),
    "inside_ratio": float(inside.mean()),
    "penetration_mean_cm": (
        float(inside_depth.mean() * 100.0)
        if inside_depth.size else 0.0
    ),
    "penetration_max_cm": (
        float(inside_depth.max() * 100.0)
        if inside_depth.size else 0.0
    ),
}

report = {
    "case": "alapuse02_v6_n60",
    "decision": "PENDING_VISUAL_AND_HAND_IDENTITY_REVIEW",
    "hand_mesh": str(HAND_PATH),
    "hand_vertices": int(len(hand.vertices)),
    "hand_faces": int(len(hand.faces)),
    "parts": part_results,
    "collision_against_watertight_whole_object": collision,
    "limitations": [
        "Only the currently available reconstructed hand is audited.",
        "Upper/lower hand identity is not yet established.",
        "Named part meshes are used only for unsigned contact distance.",
        "The complete watertight object is used for collision containment.",
    ],
}

report_path = OUT / "metrics" / f"{TOKEN}_gate_c_v0_2_report.json"
report_path.write_text(json.dumps(report, indent=2) + "\n")

hand_viz = hand.copy()
screen_viz = screen.copy()
base_viz = base.copy()

hand_viz.visual.vertex_colors = [235, 85, 85, 220]
screen_viz.visual.vertex_colors = [80, 140, 255, 180]
base_viz.visual.vertex_colors = [90, 220, 130, 180]

scene = trimesh.Scene()
scene.add_geometry(hand_viz, node_name="hand")
scene.add_geometry(screen_viz, node_name="screen_lid")
scene.add_geometry(base_viz, node_name="keyboard_base")

# Purple: nearest hand patch to lid.
for index in patch_indices["screen_lid"]:
    scene.add_geometry(
        marker(hand_vertices[index], [190, 60, 230, 255])
    )

# Orange: nearest hand patch to keyboard base.
for index in patch_indices["keyboard_base"]:
    scene.add_geometry(
        marker(hand_vertices[index], [255, 150, 40, 255])
    )

# Black: up to 40 vertices genuinely inside the watertight whole object.
inside_indices = np.flatnonzero(inside)[:40]
for index in inside_indices:
    scene.add_geometry(
        marker(hand_vertices[index], [30, 30, 30, 255])
    )

scene_path = (
    OUT
    / "visuals"
    / f"{TOKEN}_gate_c_v0_2_contact_collision_audit.glb"
)
scene.export(scene_path)

print(json.dumps(report, indent=2))
print("[OK] report:", report_path)
print("[OK] scene:", scene_path)
