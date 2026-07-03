from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit_v1_getting_unstuck"
V1A3 = FIT / "non_gt_shared_frame_recovery_v1a3"
OUT_VIS = V1A3 / "visuals"
OUT_MET = V1A3 / "metrics"
OUT_OUT = V1A3 / "outputs"
OUT_VIS.mkdir(parents=True, exist_ok=True)
OUT_MET.mkdir(parents=True, exist_ok=True)
OUT_OUT.mkdir(parents=True, exist_ok=True)

SEL_RUN = Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse01_selector_v41_refined_pipeline")
ACTIVE = CASE_ROOT / "integrated_gates/gate_a_part_repair/active_clean_parts"

paths = {
    "h2m": SEL_RUN / "h2m_transformations/alapuse01_hoi_mesh.npy",
    "guidance_hand": SEL_RUN / "guidance_out/alapuse01_hand.ply",
    "guidance_obj": SEL_RUN / "guidance_out/alapuse01_obj.ply",
    "aligned_mano": SEL_RUN / "aligned_mano/alapuse01_hamer_aligned_mano.ply",
    "active_screen": ACTIVE / "screen.ply",
    "active_base": ACTIVE / "keyboard_base.ply",
    "active_hinge": ACTIVE / "hinge.ply",
    "relabel_lid": FIT / "outputs/lid_relabel_v1.ply",
    "relabel_base": FIT / "outputs/base_relabel_v1.ply"
}

def load_mesh(path):
    if not path.exists():
        raise FileNotFoundError(path)
    obj = trimesh.load(path, force=None, process=False)
    if isinstance(obj, trimesh.Scene):
        geoms = [g for g in obj.geometry.values() if hasattr(g, "vertices") and len(g.vertices) > 0]
        if not geoms:
            raise ValueError(f"empty scene: {path}")
        return trimesh.util.concatenate(geoms)
    return obj

def colorize(mesh, rgba):
    m = mesh.copy()
    m.visual.vertex_colors = rgba
    return m

def apply_transform(mesh, T):
    m = mesh.copy()
    m.apply_transform(T)
    return m

def dist_stats(a_vertices, b_vertices):
    if len(a_vertices) == 0 or len(b_vertices) == 0:
        return {"min": None, "p1": None, "p5": None, "mean": None, "within_02": 0, "within_05": 0}
    tree = cKDTree(np.asarray(b_vertices))
    d, _ = tree.query(np.asarray(a_vertices), k=1)
    return {
        "min": float(np.min(d)),
        "p1": float(np.percentile(d, 1)),
        "p5": float(np.percentile(d, 5)),
        "mean": float(np.mean(d)),
        "within_02": int(np.sum(d < 0.02)),
        "within_05": int(np.sum(d < 0.05))
    }

def score_candidate(hand, lid, base):
    hl = dist_stats(hand.vertices, lid.vertices)
    hb = dist_stats(hand.vertices, base.vertices)

    # Higher is better. We want plausible contact to lid/screen, not base.
    lid_close = hl["within_05"]
    base_close = hb["within_05"]
    lid_p5 = hl["p5"] if hl["p5"] is not None else 999
    base_p5 = hb["p5"] if hb["p5"] is not None else 999

    score = 0.0
    score += 2.0 * lid_close
    score -= 1.0 * base_close
    score += max(0.0, 0.20 - lid_p5) * 100.0
    score -= max(0.0, 0.20 - base_p5) * 30.0

    return {
        "score": float(score),
        "hand_to_lid": hl,
        "hand_to_base": hb,
        "interpretation": "higher score means more lid/screen contact and less base contact"
    }

def mesh_info(m):
    b = np.asarray(m.bounds)
    return {
        "vertices": int(len(m.vertices)),
        "faces": int(len(m.faces)),
        "bbox_min": b[0].tolist(),
        "bbox_max": b[1].tolist(),
        "extent": (b[1] - b[0]).tolist(),
        "center": np.asarray(m.centroid).tolist()
    }

for k, p in paths.items():
    if not p.exists():
        raise FileNotFoundError(f"{k}: {p}")

H = np.load(paths["h2m"])
if H.shape != (4, 4):
    raise ValueError(f"h2m must be 4x4, got {H.shape}")
Hinv = np.linalg.inv(H)

guidance_hand = load_mesh(paths["guidance_hand"])
guidance_obj = load_mesh(paths["guidance_obj"])
aligned_mano = load_mesh(paths["aligned_mano"])

active_screen = load_mesh(paths["active_screen"])
active_base = load_mesh(paths["active_base"])
active_hinge = load_mesh(paths["active_hinge"])

relabel_lid = load_mesh(paths["relabel_lid"])
relabel_base = load_mesh(paths["relabel_base"])

identity = np.eye(4)

candidates = {
    "A_guidance_raw_active_parts_raw": {
        "hand": guidance_hand,
        "obj": guidance_obj,
        "lid": active_screen,
        "base": active_base,
        "hinge": active_hinge,
        "note": "raw selector-v41 guidance hand/object with active clean parts"
    },
    "B_guidance_h2m_active_h2m": {
        "hand": apply_transform(guidance_hand, H),
        "obj": apply_transform(guidance_obj, H),
        "lid": apply_transform(active_screen, H),
        "base": apply_transform(active_base, H),
        "hinge": apply_transform(active_hinge, H),
        "note": "apply h2m to selector-v41 guidance and active parts"
    },
    "C_guidance_h2m_relabel_raw": {
        "hand": apply_transform(guidance_hand, H),
        "obj": apply_transform(guidance_obj, H),
        "lid": relabel_lid,
        "base": relabel_base,
        "hinge": apply_transform(active_hinge, H),
        "note": "h2m hand/object with image-relabel lid/base"
    },
    "D_guidance_inv_h2m_active_inv_h2m": {
        "hand": apply_transform(guidance_hand, Hinv),
        "obj": apply_transform(guidance_obj, Hinv),
        "lid": apply_transform(active_screen, Hinv),
        "base": apply_transform(active_base, Hinv),
        "hinge": apply_transform(active_hinge, Hinv),
        "note": "apply inverse h2m to selector-v41 guidance and active parts"
    },
    "E_aligned_mano_active_raw": {
        "hand": aligned_mano,
        "obj": guidance_obj,
        "lid": active_screen,
        "base": active_base,
        "hinge": active_hinge,
        "note": "aligned_mano hand with active clean parts raw"
    }
}

report = {
    "case_id": "alapuse01",
    "stage": "Gate D-0 fit v1a3 non-GT shared-frame candidate search",
    "uses_gt": False,
    "inputs": {k: str(v) for k, v in paths.items()},
    "h2m_matrix": H.tolist(),
    "candidates": {}
}

best_name = None
best_score = -1e18

for name, c in candidates.items():
    hand, lid, base, hinge, obj = c["hand"], c["lid"], c["base"], c["hinge"], c["obj"]
    score = score_candidate(hand, lid, base)

    scene = trimesh.Scene()
    scene.add_geometry(colorize(lid, [0, 180, 255, 120]), node_name=f"{name}_lid_screen_cyan")
    scene.add_geometry(colorize(base, [255, 0, 255, 120]), node_name=f"{name}_base_magenta")
    scene.add_geometry(colorize(hinge, [255, 180, 0, 160]), node_name=f"{name}_hinge_yellow")
    scene.add_geometry(colorize(hand, [0, 255, 0, 110]), node_name=f"{name}_hand_green")
    scene.add_geometry(colorize(obj, [0, 0, 255, 45]), node_name=f"{name}_full_object_blue")

    out_glb = OUT_VIS / f"{name}.glb"
    scene.export(out_glb)

    report["candidates"][name] = {
        "note": c["note"],
        "scene": str(out_glb),
        "score": score,
        "mesh_info": {
            "hand": mesh_info(hand),
            "lid": mesh_info(lid),
            "base": mesh_info(base),
            "hinge": mesh_info(hinge)
        }
    }

    if score["score"] > best_score:
        best_score = score["score"]
        best_name = name

report["best_candidate_by_simple_contact_score"] = best_name
report["decision_rule"] = {
    "accept_candidate": "visual hand touches lid/screen and hand-to-lid is better than hand-to-base",
    "reject_all": "all candidates still put hand near base or in a wrong frame",
    "next_if_accept": "use best candidate as non-GT v1b shared-frame seed",
    "next_if_reject": "inspect original FollowMyHold transform chain around h2m_transformations and guidance_out export"
}

out_json = OUT_MET / "fit_v1a3_non_gt_shared_frame_candidates.json"
out_json.write_text(json.dumps(report, indent=2))

print("[OK] wrote", out_json)
print("[BEST]", best_name, best_score)
for name, item in report["candidates"].items():
    s = item["score"]
    print("\n==", name)
    print("scene:", item["scene"])
    print("score:", s["score"])
    print("hand_to_lid:", s["hand_to_lid"])
    print("hand_to_base:", s["hand_to_base"])
