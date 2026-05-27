from pathlib import Path
import trimesh
import numpy as np
import csv

run = Path.home() / "foho_phase0/runs/smoke_019_prompt_rect_guidance_transform_debug"
out_csv = Path.home() / "foho_phase0/inspection/prompt_ablation/smoke019_component_lineage_table.csv"

paths = [
    ("hunyuan_initial", run / "hunyuan_hoi_out/test_hoi_mesh.ply"),
    ("before_hunyuan2moge", next((run / "foho_debug").rglob("debug_obj_before_hunyuan2moge.ply")),
    ("after_hunyuan2moge", next((run / "foho_debug").rglob("debug_obj_after_hunyuan2moge.ply")),
    ("after_final_rt_scale", next((run / "foho_debug").rglob("debug_obj_after_final_rt_scale.ply")),
    ("final_debug_obj", next((run / "foho_debug").rglob("final_obj_mesh.ply")),
    ("exported_test_obj", run / "guidance_out/test_obj.ply"),
]

rows = []

for name, path in paths:
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

    comps = mesh.split(only_watertight=False)
    areas = [float(c.area) for c in comps]
    faces = [len(c.faces) for c in comps]
    verts = [len(c.vertices) for c in comps]

    largest_idx = int(np.argmax(faces)) if faces else -1
    largest_face_ratio = faces[largest_idx] / max(len(mesh.faces), 1) if faces else 0.0

    rows.append({
        "stage": name,
        "path": str(path),
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "components": len(comps),
        "watertight": bool(mesh.is_watertight),
        "area": float(mesh.area),
        "largest_component_vertices": verts[largest_idx] if faces else 0,
        "largest_component_faces": faces[largest_idx] if faces else 0,
        "largest_component_area": areas[largest_idx] if faces else 0,
        "largest_face_ratio": largest_face_ratio,
        "bounds_min": mesh.bounds[0].tolist(),
        "bounds_max": mesh.bounds[1].tolist(),
    })

out_csv.parent.mkdir(parents=True, exist_ok=True)
with out_csv.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

for row in rows:
    print(row)

print("[OK] wrote", out_csv)
