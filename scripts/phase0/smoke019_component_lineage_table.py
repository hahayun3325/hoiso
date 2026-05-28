from pathlib import Path
import csv
import numpy as np
import trimesh

run = Path.home() / "foho_phase0/runs/smoke_019_prompt_rect_guidance_transform_debug"
out_csv = Path.home() / "foho_phase0/inspection/prompt_ablation/smoke019_component_lineage_table.csv"

def first_match(root: Path, pattern: str) -> Path:
    matches = list(root.rglob(pattern))
    if not matches:
        raise FileNotFoundError(f"No file matched {pattern} under {root}")
    return matches[0]

paths = [
    ("hunyuan_initial", run / "hunyuan_hoi_out/test_hoi_mesh.ply"),
    ("before_hunyuan2moge", first_match(run / "foho_debug", "debug_obj_before_hunyuan2moge.ply")),
    ("after_hunyuan2moge", first_match(run / "foho_debug", "debug_obj_after_hunyuan2moge.ply")),
    ("after_final_rt_scale", first_match(run / "foho_debug", "debug_obj_after_final_rt_scale.ply")),
    ("final_debug_obj", first_match(run / "foho_debug", "final_obj_mesh.ply")),
    ("exported_test_obj", run / "guidance_out/test_obj.ply"),
]

rows = []

for stage, path in paths:
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

    comps = mesh.split(only_watertight=False)
    comp_faces = np.array([len(c.faces) for c in comps], dtype=np.float64)

    largest_face_ratio = float(comp_faces.max() / max(len(mesh.faces), 1)) if len(comp_faces) else 0.0
    fragmentation_score = (len(comps) - 1) + (1.0 - largest_face_ratio)

    rows.append({
        "stage": stage,
        "path": str(path),
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "components": len(comps),
        "watertight": bool(mesh.is_watertight),
        "largest_face_ratio": largest_face_ratio,
        "fragmentation_score": fragmentation_score,
        "bounds_min": mesh.bounds[0].tolist(),
        "bounds_max": mesh.bounds[1].tolist(),
    })

out_csv.parent.mkdir(parents=True, exist_ok=True)
with out_csv.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

print("stage,vertices,faces,components,watertight,largest_face_ratio,fragmentation_score")
for r in rows:
    print(
        f"{r['stage']},{r['vertices']},{r['faces']},"
        f"{r['components']},{r['watertight']},"
        f"{r['largest_face_ratio']:.6f},{r['fragmentation_score']:.6f}"
    )

print("[OK] wrote", out_csv)
