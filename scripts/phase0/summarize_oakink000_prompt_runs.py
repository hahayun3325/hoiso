from pathlib import Path
import json
import numpy as np
import pandas as pd
import trimesh

runs_root = Path.home() / "foho_phase0/runs"
csv_path = Path("docs/phase0/manual_llm_prompts/oakink000_prompt_candidates.csv")
out_csv = Path.home() / "foho_phase0/inspection/oakink_000/oakink000_prompt_run_summary.csv"
out_csv.parent.mkdir(parents=True, exist_ok=True)

def first(run, patterns):
    for pat in patterns:
        hits = sorted(run.glob(pat))
        if hits:
            return hits[0]
    return None

def load_mesh(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh

def score_mesh(path):
    if path is None or not Path(path).exists():
        return {
            "exists": False,
            "vertices": "",
            "faces": "",
            "components": "",
            "largest_face_ratio": "",
            "fragmentation_score": "",
            "watertight": "",
        }

    mesh = load_mesh(path)
    comps = mesh.split(only_watertight=False)
    faces = np.array([len(c.faces) for c in comps], dtype=float)
    largest = faces.max() / max(len(mesh.faces), 1) if len(faces) else 0.0
    frag = (len(comps) - 1) + (1.0 - largest)

    return {
        "exists": True,
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "components": len(comps),
        "largest_face_ratio": float(largest),
        "fragmentation_score": float(frag),
        "watertight": bool(mesh.is_watertight),
    }

df = pd.read_csv(csv_path)
rows = []

for _, r in df.iterrows():
    run_id = r["run_id"]
    run = runs_root / run_id

    paths = {
        "initial": first(run, ["hunyuan_hoi_out/*hoi*.ply", "hunyuan_hoi_out/*.ply"]),
        "final": first(run, ["guidance_out/*obj*.ply", "guidance_out/test_obj.ply"]),
        "selected": first(run, ["fallback_out/selected_obj.ply"]),
    }

    selector_report = run / "fallback_out/fallback_report.json"
    selector_decision = ""
    bbox_scale = ""

    if selector_report.exists():
        try:
            rep = json.loads(selector_report.read_text())
            selector_decision = rep.get("selected", "")
            bbox_scale = rep.get("bbox_scale", "")
        except Exception:
            selector_decision = "parse_error"

    for stage, path in paths.items():
        score = score_mesh(path)
        rows.append({
            "run_id": run_id,
            "llm": r["llm"],
            "prompt_style": r["prompt_style"],
            "stage": stage,
            "selector_decision": selector_decision,
            "bbox_scale": bbox_scale,
            "path": str(path) if path else "",
            **score,
        })

out = pd.DataFrame(rows)
out.to_csv(out_csv, index=False)
print("[OK] wrote", out_csv)
print(out)
