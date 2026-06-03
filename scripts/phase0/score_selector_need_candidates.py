from pathlib import Path
import argparse
import json
import numpy as np
import trimesh

ap = argparse.ArgumentParser()
ap.add_argument("--run_id", required=True)
ap.add_argument("--debug_dir", required=True)
ap.add_argument("--mock_selector_dir", required=True)
args = ap.parse_args()

run = Path.home() / f"foho_phase0/runs/{args.run_id}"
debug_dir = Path(args.debug_dir).expanduser()
mock_dir = Path(args.mock_selector_dir).expanduser()

def first_glob(base, patterns):
    for pat in patterns:
        hits = sorted(base.glob(pat))
        if hits:
            return hits[0]
    return None

def score(path):
    if path is None or not Path(path).exists():
        return {"exists": False, "path": str(path)}
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    comps = mesh.split(only_watertight=False)
    faces = np.array([len(c.faces) for c in comps], dtype=float)
    largest = faces.max() / max(len(mesh.faces), 1) if len(faces) else 0.0
    frag = (len(comps) - 1) + (1.0 - largest)
    return {
        "exists": True,
        "path": str(path),
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "components": len(comps),
        "largest_face_ratio": float(largest),
        "fragmentation_score": float(frag),
        "watertight": bool(mesh.is_watertight),
    }

paths = {
    "hunyuan_initial": first_glob(run, ["hunyuan_hoi_out/*hoi*.ply", "hunyuan_hoi_out/*.ply"]),
    "phase42_before_joint": first_glob(debug_dir, ["phase42_obj_transformed_before_joint_t4_opt0.ply", "phase42_obj_transformed_before_joint*.ply"]),
    "final_guided_obj": first_glob(run, ["guidance_out/*obj*.ply", "guidance_out/test_obj.ply"]),
    "mock_selected_phase42": mock_dir / "selected_phase42_object.ply",
}

out = {k: score(v) for k, v in paths.items()}

out_path = Path.home() / f"foho_phase0/inspection/oakink_000/{args.run_id}/selector_need_candidate_scores.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(out, indent=2))

print("[OK] wrote", out_path)
for k, v in out.items():
    print(k, "exists=", v["exists"], "comp=", v.get("components"), "frag=", v.get("fragmentation_score"))
