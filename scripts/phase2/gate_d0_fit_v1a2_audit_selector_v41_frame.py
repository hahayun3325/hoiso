from pathlib import Path
import json
import numpy as np
import trimesh

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit_v1_getting_unstuck"
REC = FIT / "selector_v41_frame_recovery_v1a2"
REC_MET = REC / "metrics"
REC_MET.mkdir(parents=True, exist_ok=True)

paths = {
    "selector_v41_aligned_pred_vs_gt_glb": CASE_ROOT / "gt_reference/visuals_alignment_audit/alapuse01_selector_v41_aligned_pred_vs_gt.glb",
    "selector_v41_aligned_decision_json": CASE_ROOT / "gt_reference/alapuse01_selector_v41_aligned_decision_v1.json",
    "selector_v41_transform_diagnostic_json": CASE_ROOT / "gt_reference/selector_v41_aligned_diagnostic/selector_v41_alignment_transform_diagnostic_v2.json",
    "selector_v41_run_root": Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse01_selector_v41_refined_pipeline"),
    "selector_v41_h2m_npy": Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse01_selector_v41_refined_pipeline/h2m_transformations/alapuse01_hoi_mesh.npy"),
    "selector_v41_guidance_hand": Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse01_selector_v41_refined_pipeline/guidance_out/alapuse01_hand.ply"),
    "selector_v41_guidance_obj": Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse01_selector_v41_refined_pipeline/guidance_out/alapuse01_obj.ply"),
    "selector_v41_aligned_mano": Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse01_selector_v41_refined_pipeline/aligned_mano/alapuse01_hamer_aligned_mano.ply"),
    "script_generate_from_hand_v2": Path("/home/fredcui/Projects/FollowMyHold/scripts/phase2/alapuse01_generate_selector_v41_aligned_from_hand_v2.py"),
    "script_make_selector_scene": Path("/home/fredcui/Projects/FollowMyHold/scripts/phase2/alapuse01_make_selector_v41_aligned_scene.py")
}

def summarize_json(p):
    if not p.exists():
        return {"exists": False}
    try:
        data = json.loads(p.read_text())
        return {
            "exists": True,
            "top_level_type": type(data).__name__,
            "keys": list(data.keys())[:50] if isinstance(data, dict) else None,
            "preview": str(data)[:1000]
        }
    except Exception as e:
        return {"exists": True, "error": repr(e)}

def summarize_npy(p):
    if not p.exists():
        return {"exists": False}
    try:
        arr = np.load(p, allow_pickle=True)
        info = {
            "exists": True,
            "type": type(arr).__name__,
            "shape": getattr(arr, "shape", None),
            "dtype": str(getattr(arr, "dtype", None))
        }
        if getattr(arr, "shape", None) == ():
            obj = arr.item()
            info["item_type"] = type(obj).__name__
            if isinstance(obj, dict):
                info["item_keys"] = list(obj.keys())
                info["item_preview"] = str(obj)[:1000]
            else:
                info["item_preview"] = str(obj)[:1000]
        else:
            info["preview"] = np.asarray(arr).reshape(-1)[:20].tolist()
        return info
    except Exception as e:
        return {"exists": True, "error": repr(e)}

def summarize_mesh_or_scene(p):
    if not p.exists():
        return {"exists": False}
    try:
        obj = trimesh.load(p, force=None, process=False)
        if isinstance(obj, trimesh.Scene):
            geoms = {}
            for name, g in obj.geometry.items():
                if hasattr(g, "vertices") and len(g.vertices) > 0:
                    geoms[name] = {
                        "num_vertices": int(len(g.vertices)),
                        "num_faces": int(len(g.faces)) if hasattr(g, "faces") else 0,
                        "bounds": np.asarray(g.bounds).tolist()
                    }
            return {"exists": True, "type": "Scene", "num_geometries": len(geoms), "geometries": geoms}
        else:
            return {
                "exists": True,
                "type": "Mesh",
                "num_vertices": int(len(obj.vertices)),
                "num_faces": int(len(obj.faces)),
                "bounds": np.asarray(obj.bounds).tolist()
            }
    except Exception as e:
        return {"exists": True, "error": repr(e)}

report = {"case_id": "alapuse01", "stage": "selector_v41_frame_recovery_v1a2_asset_audit", "paths": {}}

for k, p in paths.items():
    entry = {"path": str(p), "exists": p.exists()}
    if p.suffix.lower() == ".json":
        entry["summary"] = summarize_json(p)
    elif p.suffix.lower() == ".npy":
        entry["summary"] = summarize_npy(p)
    elif p.suffix.lower() in [".ply", ".glb"]:
        entry["summary"] = summarize_mesh_or_scene(p)
    else:
        entry["summary"] = {"exists": p.exists()}
    report["paths"][k] = entry

# Simple GT leakage hints from script source.
for script_key in ["script_generate_from_hand_v2", "script_make_selector_scene"]:
    p = paths[script_key]
    if p.exists():
        text = p.read_text(errors="ignore")
        hits = []
        for token in ["gt", "GT", "ground", "reference", "aligned", "umeyama", "procrustes", "hand_align", "h2m"]:
            if token in text:
                hits.append(token)
        report["paths"][script_key]["source_hints"] = sorted(set(hits))

out = REC_MET / "selector_v41_frame_recovery_v1a2_asset_audit.json"
out.write_text(json.dumps(report, indent=2))
print("[OK] wrote", out)
print(json.dumps(report, indent=2)[:5000])
