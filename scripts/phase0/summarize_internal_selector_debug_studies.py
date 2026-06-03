from pathlib import Path
import json
import numpy as np
import pandas as pd
import trimesh

rows = []

base_runs = [
    "oakink000_gpt54thinking_short",
    "oakink000_gemini31pro_short",
    "oakink000_sonnet46thinking_short",
    "oakink000_gpt55_short",
    "oakink000_gpt55thinking_short",
]

def score(path):
    path = Path(path)
    if not path.exists():
        return None
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    comps = mesh.split(only_watertight=False)
    faces = np.array([len(c.faces) for c in comps], dtype=float)
    largest = faces.max() / max(len(mesh.faces), 1) if len(faces) else 0.0
    frag = (len(comps) - 1) + (1.0 - largest)
    return {
        "components": len(comps),
        "fragmentation_score": float(frag),
        "largest_face_ratio": float(largest),
        "faces": len(mesh.faces),
    }

def first_glob(base, patterns):
    for pat in patterns:
        hits = sorted(base.glob(pat))
        if hits:
            return hits[0]
    return None

for base_id in base_runs:
    debug_id = f"{base_id}_selector_debug"
    run = Path.home() / "foho_phase0/runs" / debug_id
    debug_dir = Path.home() / "foho_phase0/inspection/oakink_000" / debug_id / "internal_selector_debug"
    mock_dir = Path.home() / "foho_phase0/inspection/oakink_000" / base_id / "phase42_selector_mock"

    candidates = {
        "hunyuan_initial": first_glob(run, ["hunyuan_hoi_out/*hoi*.ply", "hunyuan_hoi_out/*.ply"]),
        "phase42_before_joint": first_glob(debug_dir, ["phase42_obj_transformed_before_joint_t4_opt0.ply", "phase42_obj_transformed_before_joint*.ply"]),
        "final_guided_obj": first_glob(run, ["guidance_out/*obj*.ply", "guidance_out/test_obj.ply"]),
        "mock_selected": mock_dir / "selected_phase42_object.ply",
    }

    selected_name = ""
    report = mock_dir / "phase42_object_selection_report.json"
    if report.exists():
        try:
            selected_name = json.loads(report.read_text()).get("selected_name", "")
        except Exception:
            selected_name = "parse_error"

    for stage, path in candidates.items():
        s = score(path) if path else None
        rows.append({
            "base_run": base_id,
            "debug_run": debug_id,
            "stage": stage,
            "selected_name": selected_name,
            "path": str(path) if path else "",
            "exists": s is not None,
            **(s or {}),
        })

df = pd.DataFrame(rows)
out_csv = Path.home() / "foho_phase0/inspection/oakink_000/internal_selector_debug_summary.csv"
out_md = Path("docs/phase0/oakink000_internal_selector_debug_summary.md")

out_csv.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out_csv, index=False)

with out_md.open("w") as f:
    f.write("# OakInk split000 — Internal Selector Debug Summary\n\n")
    f.write(df.to_markdown(index=False))
    f.write("\n")

print("[OK] wrote", out_csv)
print("[OK] wrote", out_md)
print(df)
