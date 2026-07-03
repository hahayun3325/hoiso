from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit_v1_getting_unstuck"
V1A7 = FIT / "corrected_scale_root_pose_probe_v1a7"
V1A8 = FIT / "root_pose_provenance_audit_v1a8"

SEL_RUN = Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse01_selector_v41_refined_pipeline")
ACTIVE = CASE_ROOT / "integrated_gates/gate_a_part_repair/active_clean_parts"

VIS = V1A8 / "visuals"
MET = V1A8 / "metrics"
OUT = V1A8 / "outputs"
for p in [VIS, MET, OUT]:
    p.mkdir(parents=True, exist_ok=True)

def load_mesh(path):
    path = Path(path)
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

def bbox_info(mesh):
    b = np.asarray(mesh.bounds, dtype=float)
    ext = b[1] - b[0]
    return {
        "num_vertices": int(len(mesh.vertices)),
        "num_faces": int(len(mesh.faces)),
        "bbox_min": b[0].tolist(),
        "bbox_max": b[1].tolist(),
        "extent_xyz": ext.tolist(),
        "xy_max_extent": float(ext[:2].max()),
        "max_extent": float(ext.max()),
        "center": np.asarray(mesh.centroid).tolist()
    }

def translate(mesh, vec):
    out = mesh.copy()
    out.apply_translation(np.asarray(vec))
    return out

def sample(mesh, n=10000, seed=0):
    rng = np.random.default_rng(seed)
    if len(mesh.faces) > 0:
        pts, _ = trimesh.sample.sample_surface(mesh, n)
        return pts
    v = np.asarray(mesh.vertices)
    if len(v) <= n:
        return v
    return v[rng.choice(len(v), n, replace=False)]

def nearest_stats(A, B):
    tree = cKDTree(B)
    d, _ = tree.query(A, k=1)
    return {
        "min": float(np.min(d)),
        "p1": float(np.percentile(d, 1)),
        "p5": float(np.percentile(d, 5)),
        "p10": float(np.percentile(d, 10)),
        "mean": float(np.mean(d)),
        "within_02": int(np.sum(d < 0.02)),
        "within_05": int(np.sum(d < 0.05))
    }

def export_scene(name, hand, screen, base, hinge, extra=None):
    scene = trimesh.Scene()
    scene.add_geometry(colorize(hand, [0, 255, 0, 130]), node_name="hand_green")
    scene.add_geometry(colorize(screen, [0, 190, 255, 150]), node_name="screen_lid_cyan")
    scene.add_geometry(colorize(base, [255, 0, 255, 140]), node_name="base_magenta")
    scene.add_geometry(colorize(hinge, [255, 180, 0, 180]), node_name="hinge_yellow")
    if extra:
        for node_name, mesh, rgba in extra:
            scene.add_geometry(colorize(mesh, rgba), node_name=node_name)
    out = VIS / f"{name}.glb"
    scene.export(out)
    return str(out)

# Inputs
aligned_mano = load_mesh(SEL_RUN / "aligned_mano/alapuse01_hamer_aligned_mano.ply")
guidance_hand = load_mesh(SEL_RUN / "guidance_out/alapuse01_hand.ply")
guidance_obj = load_mesh(SEL_RUN / "guidance_out/alapuse01_obj.ply")

screen_active = load_mesh(ACTIVE / "screen.ply")
base_active = load_mesh(ACTIVE / "keyboard_base.ply")
hinge_active = load_mesh(ACTIVE / "hinge.ply")

# v1a7 corrected-scale outputs
hand_scaled = load_mesh(V1A7 / "outputs/hand_aligned_mano_scaled_to_guidance_bbox_v1a7.ply")
screen_scaled = load_mesh(V1A7 / "outputs/screen_object_scaled_v1a7.ply")
base_scaled = load_mesh(V1A7 / "outputs/base_object_scaled_v1a7.ply")
hinge_scaled = load_mesh(V1A7 / "outputs/hinge_object_scaled_v1a7.ply")

v1a7_report = json.loads((V1A7 / "metrics/fit_v1a7_corrected_scale_root_pose_probe.json").read_text())

# Centers
infos = {
    "aligned_mano_raw": bbox_info(aligned_mano),
    "guidance_hand": bbox_info(guidance_hand),
    "guidance_obj": bbox_info(guidance_obj),
    "active_screen": bbox_info(screen_active),
    "active_base": bbox_info(base_active),
    "active_hinge": bbox_info(hinge_active),
    "v1a7_hand_scaled": bbox_info(hand_scaled),
    "v1a7_screen_scaled": bbox_info(screen_scaled),
    "v1a7_base_scaled": bbox_info(base_scaled),
    "v1a7_hinge_scaled": bbox_info(hinge_scaled)
}

def center(name):
    return np.asarray(infos[name]["center"], dtype=float)

# Candidate root pose repairs / diagnostics
# 1. v1a7 no-translation baseline
# 2. translate scaled aligned_mano hand to guidance_hand center
# 3. translate scaled object to guidance_obj center
# 4. translate both scaled hand and scaled object to guidance centers
# 5. raw guidance scene

delta_hand_to_guidance = center("guidance_hand") - center("v1a7_hand_scaled")
delta_obj_to_guidance = center("guidance_obj") - np.mean([
    center("v1a7_screen_scaled"),
    center("v1a7_base_scaled"),
    center("v1a7_hinge_scaled")
], axis=0)

candidates = {}

candidates["A_v1a7_scaled_no_translation"] = {
    "hand": hand_scaled,
    "screen": screen_scaled,
    "base": base_scaled,
    "hinge": hinge_scaled,
    "note": "same as v1a7 A; corrected scale but no root translation"
}

candidates["B_hand_scaled_to_guidance_hand_center"] = {
    "hand": translate(hand_scaled, delta_hand_to_guidance),
    "screen": screen_scaled,
    "base": base_scaled,
    "hinge": hinge_scaled,
    "note": "tests whether aligned_mano lost root translation relative to guidance_hand"
}

candidates["C_object_scaled_to_guidance_obj_center"] = {
    "hand": hand_scaled,
    "screen": translate(screen_scaled, delta_obj_to_guidance),
    "base": translate(base_scaled, delta_obj_to_guidance),
    "hinge": translate(hinge_scaled, delta_obj_to_guidance),
    "note": "tests whether active object parts are in a different root frame from guidance_obj"
}

candidates["D_both_scaled_to_guidance_centers"] = {
    "hand": translate(hand_scaled, delta_hand_to_guidance),
    "screen": translate(screen_scaled, delta_obj_to_guidance),
    "base": translate(base_scaled, delta_obj_to_guidance),
    "hinge": translate(hinge_scaled, delta_obj_to_guidance),
    "note": "tests whether guidance_out hand/object centers define a coherent non-GT frame"
}

# For raw guidance object, we cannot split parts, so show it as extra blue object with active parts for reference.
candidates["E_raw_guidance_hand_with_active_parts"] = {
    "hand": guidance_hand,
    "screen": screen_active,
    "base": base_active,
    "hinge": hinge_active,
    "extra": [("raw_guidance_obj_blue", guidance_obj, [0, 0, 255, 70])],
    "note": "raw guidance hand/object reference; shows whether guidance frame itself is coherent"
}

report_candidates = {}
for name, c in candidates.items():
    hand = c["hand"]
    screen = c["screen"]
    base = c["base"]
    hinge = c["hinge"]
    screen_pts = sample(screen, 12000, seed=1)
    base_pts = sample(base, 12000, seed=2)
    hand_v = np.asarray(hand.vertices)

    h2screen = nearest_stats(hand_v, screen_pts)
    h2base = nearest_stats(hand_v, base_pts)

    scene_path = export_scene(
        name,
        hand,
        screen,
        base,
        hinge,
        extra=c.get("extra")
    )

    report_candidates[name] = {
        "note": c["note"],
        "scene": scene_path,
        "hand_to_screen": h2screen,
        "hand_to_base": h2base,
        "mesh_infos": {
            "hand": bbox_info(hand),
            "screen": bbox_info(screen),
            "base": bbox_info(base),
            "hinge": bbox_info(hinge)
        }
    }

# Transform file inventory
transform_files = []
for p in SEL_RUN.rglob("*"):
    if p.is_file() and (
        "transform" in p.name.lower()
        or "h2m" in p.name.lower()
        or "m2h" in p.name.lower()
        or "pose" in p.name.lower()
        or p.suffix.lower() in [".npy", ".json"]
    ):
        transform_files.append(str(p))

decision = "VISUAL_CHECK_REQUIRED"
next_step = "open candidate scenes and decide which branch explains the 42 cm root gap"

report = {
    "case_id": "alapuse01",
    "stage": "Gate D-0 fit v1a8 root-pose provenance audit",
    "uses_gt": False,
    "v1a7_decision": v1a7_report.get("decision"),
    "v1a7_snap_norm_full": v1a7_report.get("snap", {}).get("snap_norm_full"),
    "centers_and_bboxes": infos,
    "root_deltas": {
        "delta_hand_scaled_to_guidance_hand_center": delta_hand_to_guidance.tolist(),
        "delta_hand_scaled_to_guidance_hand_norm": float(np.linalg.norm(delta_hand_to_guidance)),
        "delta_object_scaled_to_guidance_obj_center": delta_obj_to_guidance.tolist(),
        "delta_object_scaled_to_guidance_obj_norm": float(np.linalg.norm(delta_obj_to_guidance))
    },
    "candidates": report_candidates,
    "selector_v41_transform_like_files": transform_files,
    "decision": decision,
    "decision_rule": {
        "if_B_improves": "aligned_mano lost root translation; use guidance_hand root with scaled aligned_mano geometry",
        "if_C_improves": "active object parts are in wrong root frame; recover object root from guidance_obj",
        "if_D_improves": "guidance_out centers provide a coherent non-GT frame",
        "if_E_only_good_but_wrong_part": "raw guidance frame is coherent but semantic contact/part pose is wrong",
        "if_none_good": "inspect FollowMyHold export/render chain line by line"
    },
    "next_step": next_step
}

out = MET / "fit_v1a8_root_pose_provenance_audit.json"
out.write_text(json.dumps(report, indent=2))

print("[OK] wrote", out)
print("[v1a7_decision]", report["v1a7_decision"])
print("[v1a7_snap_norm_full]", report["v1a7_snap_norm_full"])
print("[root_deltas]", json.dumps(report["root_deltas"], indent=2))
print("[scenes]")
for k, v in report_candidates.items():
    print(k, "->", v["scene"])
    print("  h2screen mean:", v["hand_to_screen"]["mean"], "within05:", v["hand_to_screen"]["within_05"])
    print("  h2base mean:", v["hand_to_base"]["mean"], "within05:", v["hand_to_base"]["within_05"])
