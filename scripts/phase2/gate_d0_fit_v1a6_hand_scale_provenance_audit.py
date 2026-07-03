from pathlib import Path
import json
import numpy as np
import trimesh

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit_v1_getting_unstuck"
V1A5 = FIT / "scale_frame_audit_v1a5"
V1A6 = FIT / "hand_scale_provenance_audit_v1a6"

SEL_RUN = Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse01_selector_v41_refined_pipeline")
ACTIVE = CASE_ROOT / "integrated_gates/gate_a_part_repair/active_clean_parts"

VIS = V1A6 / "visuals"
MET = V1A6 / "metrics"
OUT = V1A6 / "outputs"
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

def transform_mesh(mesh, T):
    out = mesh.copy()
    out.apply_transform(T)
    return out

def scale_mesh_about_center(mesh, scale):
    out = mesh.copy()
    c = np.asarray(out.centroid)
    v = np.asarray(out.vertices)
    out.vertices = (v - c) * scale + c
    return out

def center_mesh_to(mesh, target_center):
    out = mesh.copy()
    out.apply_translation(np.asarray(target_center) - np.asarray(out.centroid))
    return out

def export_scene(path, items):
    scene = trimesh.Scene()
    for name, mesh, rgba in items:
        scene.add_geometry(colorize(mesh, rgba), node_name=name)
    scene.export(path)
    return str(path)

# Known assets
paths = {
    "aligned_mano": SEL_RUN / "aligned_mano/alapuse01_hamer_aligned_mano.ply",
    "guidance_hand": SEL_RUN / "guidance_out/alapuse01_hand.ply",
    "guidance_obj": SEL_RUN / "guidance_out/alapuse01_obj.ply",
    "h2m": SEL_RUN / "h2m_transformations/alapuse01_hoi_mesh.npy",
    "active_screen": ACTIVE / "screen.ply",
    "active_base": ACTIVE / "keyboard_base.ply",
    "active_hinge": ACTIVE / "hinge.ply",
    "v1a5_report": V1A5 / "metrics/fit_v1a5_scale_frame_audit.json"
}

# Search for additional hand-like files for provenance.
search_roots = [SEL_RUN, CASE_ROOT]
extra_hand_files = []
for root in search_roots:
    if root.exists():
        for p in root.rglob("*"):
            if p.suffix.lower() in [".ply", ".obj", ".glb"] and any(tok in p.name.lower() for tok in ["hand", "mano", "hamer"]):
                if p not in paths.values():
                    extra_hand_files.append(p)

for k, p in paths.items():
    if k != "v1a5_report" and not p.exists():
        print("[WARN missing]", k, p)

aligned = load_mesh(paths["aligned_mano"])
guidance_hand = load_mesh(paths["guidance_hand"])
guidance_obj = load_mesh(paths["guidance_obj"])
screen = load_mesh(paths["active_screen"])
base = load_mesh(paths["active_base"])
hinge = load_mesh(paths["active_hinge"])
active_obj = trimesh.util.concatenate([screen, base, hinge])

# Load h2m and decompose approximate scale.
h2m_info = {"exists": paths["h2m"].exists()}
H = None
if paths["h2m"].exists():
    arr = np.load(paths["h2m"], allow_pickle=True)
    if getattr(arr, "shape", None) == (4, 4):
        H = arr.astype(float)
    elif getattr(arr, "shape", None) == ():
        item = arr.item()
        if isinstance(item, dict):
            for key in ["h2m", "H", "T", "transform", "matrix", "alapuse01_hoi_mesh"]:
                if key in item:
                    cand = np.asarray(item[key])
                    if cand.shape == (4, 4):
                        H = cand.astype(float)
                        h2m_info["matrix_key"] = key
                        break
    if H is not None:
        A = H[:3, :3]
        sv = np.linalg.svd(A, compute_uv=False)
        det_scale = abs(np.linalg.det(A)) ** (1.0 / 3.0)
        h2m_info.update({
            "matrix": H.tolist(),
            "singular_values": sv.tolist(),
            "approx_uniform_scale_from_det": float(det_scale),
            "approx_uniform_scale_from_svd_mean": float(np.mean(sv)),
            "translation": H[:3, 3].tolist()
        })
    else:
        h2m_info["load_warning"] = f"Could not parse 4x4 matrix from {paths['h2m']}"

# Basic mesh scale info
mesh_infos = {
    "aligned_mano": bbox_info(aligned),
    "guidance_hand": bbox_info(guidance_hand),
    "guidance_obj": bbox_info(guidance_obj),
    "active_object": bbox_info(active_obj),
    "screen": bbox_info(screen),
    "base": bbox_info(base),
    "hinge": bbox_info(hinge)
}

# Ratio comparisons
def safe_ratio(a, b):
    return float(a / b) if b and abs(b) > 1e-12 else None

ratios = {
    "aligned_mano_xy_over_guidance_hand_xy": safe_ratio(mesh_infos["aligned_mano"]["xy_max_extent"], mesh_infos["guidance_hand"]["xy_max_extent"]),
    "aligned_mano_max_over_guidance_hand_max": safe_ratio(mesh_infos["aligned_mano"]["max_extent"], mesh_infos["guidance_hand"]["max_extent"]),
    "guidance_hand_xy_over_active_object_xy": safe_ratio(mesh_infos["guidance_hand"]["xy_max_extent"], mesh_infos["active_object"]["xy_max_extent"]),
    "aligned_mano_xy_over_active_object_xy": safe_ratio(mesh_infos["aligned_mano"]["xy_max_extent"], mesh_infos["active_object"]["xy_max_extent"])
}

# Also test what happens if h2m is applied to guidance_hand.
if H is not None:
    guidance_h2m = transform_mesh(guidance_hand, H)
    mesh_infos["guidance_hand_h2m"] = bbox_info(guidance_h2m)
    ratios["guidance_hand_h2m_xy_over_active_object_xy"] = safe_ratio(mesh_infos["guidance_hand_h2m"]["xy_max_extent"], mesh_infos["active_object"]["xy_max_extent"])
else:
    guidance_h2m = None

# Diagnostic scenes
scene_paths = {}

# Scene 1: actual E-style candidate with aligned_mano + active object
scene_paths["E_aligned_mano_active_object"] = export_scene(
    VIS / "E_aligned_mano_active_object.glb",
    [
        ("aligned_mano_green", aligned, [0, 255, 0, 130]),
        ("screen_cyan", screen, [0, 190, 255, 150]),
        ("base_magenta", base, [255, 0, 255, 140]),
        ("hinge_yellow", hinge, [255, 180, 0, 180])
    ]
)

# Scene 2: guidance_hand in same active-object scene
scene_paths["guidance_hand_active_object"] = export_scene(
    VIS / "guidance_hand_active_object.glb",
    [
        ("guidance_hand_green", guidance_hand, [0, 255, 0, 130]),
        ("screen_cyan", screen, [0, 190, 255, 150]),
        ("base_magenta", base, [255, 0, 255, 140]),
        ("hinge_yellow", hinge, [255, 180, 0, 180])
    ]
)

# Scene 3: h2m guidance hand if available
if guidance_h2m is not None:
    scene_paths["guidance_hand_h2m_active_object"] = export_scene(
        VIS / "guidance_hand_h2m_active_object.glb",
        [
            ("guidance_hand_h2m_green", guidance_h2m, [0, 255, 0, 130]),
            ("screen_cyan", screen, [0, 190, 255, 150]),
            ("base_magenta", base, [255, 0, 255, 140]),
            ("hinge_yellow", hinge, [255, 180, 0, 180])
        ]
    )

# Scene 4: centered hand scale comparison
target_c = np.zeros(3)
aligned_c = center_mesh_to(aligned, target_c)
guidance_c = center_mesh_to(guidance_hand, target_c)
scene_paths["centered_aligned_vs_guidance_hand"] = export_scene(
    VIS / "centered_aligned_vs_guidance_hand.glb",
    [
        ("aligned_mano_green", aligned_c, [0, 255, 0, 110]),
        ("guidance_hand_gray", guidance_c, [120, 120, 120, 110])
    ]
)

# Scene 5: aligned_mano scaled to guidance bbox, placed with active object
scale_aligned_to_guidance = None
if mesh_infos["aligned_mano"]["xy_max_extent"] > 1e-12:
    scale_aligned_to_guidance = mesh_infos["guidance_hand"]["xy_max_extent"] / mesh_infos["aligned_mano"]["xy_max_extent"]
    aligned_scaled = scale_mesh_about_center(aligned, scale_aligned_to_guidance)
    scene_paths["aligned_mano_scaled_to_guidance_bbox_active_object"] = export_scene(
        VIS / "aligned_mano_scaled_to_guidance_bbox_active_object.glb",
        [
            ("aligned_mano_scaled_green", aligned_scaled, [0, 255, 0, 130]),
            ("screen_cyan", screen, [0, 190, 255, 150]),
            ("base_magenta", base, [255, 0, 255, 140]),
            ("hinge_yellow", hinge, [255, 180, 0, 180])
        ]
    )

# Summarize extra hand files lightly
extra = []
for p in sorted(extra_hand_files)[:50]:
    try:
        m = load_mesh(p)
        extra.append({"path": str(p), "info": bbox_info(m)})
    except Exception as e:
        extra.append({"path": str(p), "error": repr(e)})

flags = []
decision = "UNDECIDED_VISUAL_CHECK_REQUIRED"

if ratios["aligned_mano_xy_over_guidance_hand_xy"] is not None and ratios["aligned_mano_xy_over_guidance_hand_xy"] > 1.25:
    flags.append("ALIGNED_MANO_LARGER_THAN_GUIDANCE_HAND")
if ratios["guidance_hand_xy_over_active_object_xy"] is not None and ratios["guidance_hand_xy_over_active_object_xy"] > 1.2:
    flags.append("GUIDANCE_HAND_ALREADY_LARGE_RELATIVE_TO_ACTIVE_OBJECT")
if ratios["aligned_mano_xy_over_active_object_xy"] is not None and ratios["aligned_mano_xy_over_active_object_xy"] > 1.2:
    flags.append("ALIGNED_MANO_LARGE_RELATIVE_TO_ACTIVE_OBJECT")
if h2m_info.get("approx_uniform_scale_from_det") and abs(h2m_info["approx_uniform_scale_from_det"] - 1.0) > 0.15:
    flags.append("H2M_HAS_NONTRIVIAL_SCALE_TERM")

if "ALIGNED_MANO_LARGER_THAN_GUIDANCE_HAND" in flags:
    decision = "HAND_SCALE_PROVENANCE_SUSPECT_ALIGNED_MANO"
elif "GUIDANCE_HAND_ALREADY_LARGE_RELATIVE_TO_ACTIVE_OBJECT" in flags:
    decision = "HAND_OBJECT_SCALE_MISMATCH_ALREADY_IN_GUIDANCE_FRAME"
elif "H2M_HAS_NONTRIVIAL_SCALE_TERM" in flags:
    decision = "H2M_SCALE_TERM_NEEDS_REPLAY_CHECK"
else:
    decision = "NO_CLEAR_HAND_SCALE_BUG_FROM_BBOX_ONLY"

report = {
    "case_id": "alapuse01",
    "stage": "Gate D-0 fit v1a6 hand-scale/provenance audit",
    "uses_gt": False,
    "paths": {k: str(v) for k, v in paths.items()},
    "mesh_infos": mesh_infos,
    "ratios": ratios,
    "h2m_info": h2m_info,
    "scale_aligned_mano_to_guidance_bbox": scale_aligned_to_guidance,
    "extra_hand_like_files": extra,
    "flags": flags,
    "decision": decision,
    "scenes": scene_paths,
    "decision_rule": {
        "aligned_mano_scale_bug": "aligned_mano much larger than guidance_hand",
        "guidance_hand_scale_bug": "guidance_hand already much larger than active object",
        "h2m_scale_bug": "h2m has a nontrivial uniform scale term",
        "need_visual": "open scenes before deciding which hand source to use"
    },
    "next_step": "inspect scenes and decide whether to use guidance_hand, rescale aligned_mano, or debug h2m transform chain"
}

out = MET / "fit_v1a6_hand_scale_provenance_audit.json"
out.write_text(json.dumps(report, indent=2))

print("[OK] wrote", out)
print("[decision]", decision)
print("[flags]", flags)
print("[ratios]", json.dumps(ratios, indent=2))
print("[h2m_info]", json.dumps(h2m_info, indent=2)[:1000])
print("[scenes]")
for k, v in scene_paths.items():
    print(k, "->", v)
