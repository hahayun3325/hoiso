from pathlib import Path
import pandas as pd
import trimesh

HOME = Path.home()

SURF = HOME / "foho_phase0/inspection/arctic_phase017/paper_style_eval_selected_cases_surface/arctic_selected_cases_surface_paperstyle_metrics.csv"
OUT_DIR = HOME / "foho_phase0/inspection/arctic_phase017/final_report_assets"
OUT = OUT_DIR / "arctic_selected_paper_like_metrics_surface.csv"

OUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(SURF)
df = df[df["status"] == "ok"].copy()

def obj_mesh_stats(path):
    try:
        mesh = trimesh.load(path, process=False)
        if isinstance(mesh, trimesh.Scene):
            mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

        comps = mesh.split(only_watertight=False)
        n_comp = len(comps)
        faces_total = max(len(mesh.faces), 1)
        largest_face_ratio = max([len(c.faces) for c in comps], default=0) / faces_total
        fragmentation = max(n_comp - largest_face_ratio, 0.0)

        return {
            "pred_obj_components": n_comp,
            "pred_obj_fragmentation": fragmentation,
            "pred_obj_largest_face_ratio": largest_face_ratio,
            "pred_obj_watertight": bool(mesh.is_watertight),
        }
    except Exception:
        return {
            "pred_obj_components": -1,
            "pred_obj_fragmentation": -1,
            "pred_obj_largest_face_ratio": -1,
            "pred_obj_watertight": False,
        }

rows = []
for _, r in df.iterrows():
    stats = obj_mesh_stats(r["object_mesh"])
    label = "baseline" if r["method"] == "default" else "gpt55_selector"

    row = {
        "case": r["case"],
        "label": label,
        "method": r["method"],
        "align_mode": "surface_sampled_hand_aligned",
        "fixed_gt_hand": r["fixed_gt_hand"],
        "status": r["status"],
        "object_cd_m": r["object_cd_mm"] / 1000.0,
        "object_cd_mm": r["object_cd_mm"],
        "f5": r["object_f5"],
        "f10": r["object_f10"],
        "precision_5mm": r["object_precision_5mm"],
        "recall_5mm": r["object_recall_5mm"],
        "precision_10mm": r["object_precision_10mm"],
        "recall_10mm": r["object_recall_10mm"],
        "hand_align_cd_mm": r["hand_cd_mm"],
        "sim_scale": r["sim_scale"],
        "n_surface_samples": r["n_surface_samples"],
        "pred_hand_path": r["hand_mesh"],
        "pred_obj_path": r["object_mesh"],
        **stats,
    }
    rows.append(row)

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

print("[OK] wrote", OUT)
print(out.to_string(index=False))
