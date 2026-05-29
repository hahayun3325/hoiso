from pathlib import Path
import os
import json
import shutil
import numpy as np
import trimesh

enable = os.environ.get("FOHO_ENABLE_OBJECT_FALLBACK", "0") == "1"
mode = os.environ.get("FOHO_FALLBACK_ALIGN_MODE", "none")

run_dir = Path(os.environ["FOHO_RUN_DIR"])
initial_obj = Path(os.environ.get(
    "FOHO_INITIAL_OBJECT",
    str(run_dir / "hunyuan_hoi_out/test_hoi_mesh.ply")
))
final_obj = run_dir / "guidance_out/test_obj.ply"
final_hand = run_dir / "guidance_out/test_hand.ply"

out_dir = run_dir / "fallback_out"
out_dir.mkdir(parents=True, exist_ok=True)

def load_mesh(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh

def score_mesh(path):
    mesh = load_mesh(path)
    comps = mesh.split(only_watertight=False)
    faces = np.array([len(c.faces) for c in comps], dtype=float)
    largest_ratio = faces.max() / max(len(mesh.faces), 1) if len(faces) else 0.0
    frag_score = (len(comps) - 1) + (1.0 - largest_ratio)
    return {
        "path": str(path),
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "components": len(comps),
        "watertight": bool(mesh.is_watertight),
        "largest_face_ratio": float(largest_ratio),
        "fragmentation_score": float(frag_score),
    }

def bbox_align(source, target):
    src = source.copy()
    src_center = src.bounds.mean(axis=0)
    src_extent = src.bounds[1] - src.bounds[0]

    tgt_center = target.bounds.mean(axis=0)
    tgt_extent = target.bounds[1] - target.bounds[0]

    scale = np.linalg.norm(tgt_extent) / max(np.linalg.norm(src_extent), 1e-8)
    src.vertices = (src.vertices - src_center) * scale + tgt_center
    return src, scale

report = {
    "enabled": enable,
    "mode": mode,
    "run_dir": str(run_dir),
}

if not enable:
    report["selected"] = "final_obj_original"
    shutil.copy2(final_obj, out_dir / "selected_obj.ply")
    shutil.copy2(final_hand, out_dir / "selected_hand.ply")
else:
    scores = {
        "initial_obj": score_mesh(initial_obj),
        "final_obj": score_mesh(final_obj),
    }

    selected = min(scores.keys(), key=lambda k: scores[k]["fragmentation_score"])
    selected_path = Path(scores[selected]["path"])

    selected_mesh = load_mesh(selected_path)

    if mode == "bbox" and selected == "initial_obj":
        target_mesh = load_mesh(final_obj)
        selected_mesh, scale = bbox_align(selected_mesh, target_mesh)
        report["bbox_scale"] = float(scale)

    selected_mesh.export(out_dir / "selected_obj.ply")
    shutil.copy2(final_hand, out_dir / "selected_hand.ply")

    scene = trimesh.Scene()
    scene.add_geometry(selected_mesh, geom_name="selected_object")
    scene.add_geometry(load_mesh(final_hand), geom_name="final_hand")
    scene.export(out_dir / "fallback_scene.glb")

    try:
        (out_dir / "fallback_scene.png").write_bytes(scene.save_image(resolution=(1400, 1000)))
    except Exception as e:
        report["render_error"] = repr(e)

    report["scores"] = scores
    report["selected"] = selected

report_path = out_dir / "fallback_report.json"
report_path.write_text(json.dumps(report, indent=2))

print(json.dumps(report, indent=2))
print("[OK] wrote", out_dir)
