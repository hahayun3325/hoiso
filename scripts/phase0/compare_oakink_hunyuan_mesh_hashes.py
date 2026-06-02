from pathlib import Path
import hashlib
import pandas as pd
import trimesh
import numpy as np

def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def first(run, patterns):
    for pat in patterns:
        hits = sorted(run.glob(pat))
        if hits:
            return hits[0]
    return None

def mesh_stats(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return {
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "bounds_min": np.round(mesh.bounds[0], 5).tolist(),
        "bounds_max": np.round(mesh.bounds[1], 5).tolist(),
    }

csv_path = Path("docs/phase0/manual_llm_prompts/oakink000_prompt_candidates_short.csv")
df = pd.read_csv(csv_path)

print("run_id,llm,inpaint_md5,hunyuan_md5,vertices,faces,bounds_min,bounds_max")

for _, r in df.iterrows():
    run = Path.home() / "foho_phase0/runs" / r["run_id"]

    inpaint = first(run, ["ours_inpaint/*inpainted*.png"])
    hunyuan = first(run, ["hunyuan_hoi_out/*hoi*.ply", "hunyuan_hoi_out/*.ply"])

    if not inpaint or not hunyuan:
        print(f"{r['run_id']},{r['llm']},MISSING,MISSING,,,,")
        continue

    st = mesh_stats(hunyuan)
    print(
        f"{r['run_id']},{r['llm']},"
        f"{md5_file(inpaint)},{md5_file(hunyuan)},"
        f"{st['vertices']},{st['faces']},"
        f"\"{st['bounds_min']}\",\"{st['bounds_max']}\""
    )
