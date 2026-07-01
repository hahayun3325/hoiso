from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT_ROOT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit"
MANIFEST = FIT_ROOT / "metrics/standalone_fitter_input_manifest.json"

OUT = CASE_ROOT / "integrated_gates/gate_c_v3_lite"
OUT_METRICS = OUT / "metrics"
OUT_VIS = OUT / "visuals"
OUT_METRICS.mkdir(parents=True, exist_ok=True)
OUT_VIS.mkdir(parents=True, exist_ok=True)

ACTIVE = CASE_ROOT / "integrated_gates/gate_a_part_repair/active_clean_parts"

def load_mesh(path):
    obj = trimesh.load(path, force=None, process=False)
    if isinstance(obj, trimesh.Scene):
        geoms = [g for g in obj.geometry.values() if hasattr(g, "vertices") and len(g.vertices) > 0]
        return trimesh.util.concatenate(geoms)
    return obj

def colorize(mesh, rgba):
    m = mesh.copy()
    m.visual.vertex_colors = rgba
    return m

def marker(center, radius, rgba):
    s = trimesh.creation.icosphere(subdivisions=2, radius=radius)
    s.apply_translation(center)
    s.visual.vertex_colors = rgba
    return s

data = json.loads(MANIFEST.read_text())
paths = {k: Path(v["path"]) for k, v in data["paths"].items() if v["exists"]}

screen = load_mesh(ACTIVE / "screen.ply")
base = load_mesh(ACTIVE / "keyboard_base.ply")
hinge = load_mesh(ACTIVE / "hinge.ply")
hand = load_mesh(paths["guidance_hand"])

# Try to use HaMeR keypoints for finger-level lite verification.
kps_path = paths.get("hamer_kps", None)
kps = None
if kps_path and kps_path.exists():
    arr = np.load(kps_path, allow_pickle=True)
    if isinstance(arr, np.ndarray) and arr.dtype == object:
        obj = arr.item() if arr.shape == () else arr
        if isinstance(obj, dict):
            for v in obj.values():
                vv = np.asarray(v)
                if vv.ndim >= 2 and vv.shape[-1] == 3 and vv.reshape(-1, 3).shape[0] >= 21:
                    kps = vv.reshape(-1, 3)[:21]
                    break
    else:
        vv = np.asarray(arr)
        if vv.ndim >= 2 and vv.shape[-1] == 3 and vv.reshape(-1, 3).shape[0] >= 21:
            kps = vv.reshape(-1, 3)[:21]

screen_pts = np.asarray(screen.vertices)
screen_tree = cKDTree(screen_pts)

base_pts = np.asarray(base.vertices)
base_tree = cKDTree(base_pts)

# MANO-like convention: index tip 8, middle tip 12, ring tip 16.
finger_ids = {
    "index_tip": 8,
    "middle_tip": 12,
    "ring_tip": 16
}

contacts = {}
scene = trimesh.Scene()
scene.add_geometry(colorize(screen, [0, 0, 255, 150]), node_name="active_screen_blue")
scene.add_geometry(colorize(base, [255, 140, 0, 180]), node_name="active_keyboard_base_orange")
scene.add_geometry(colorize(hinge, [255, 0, 255, 220]), node_name="active_hinge_magenta")
scene.add_geometry(colorize(hand, [0, 255, 0, 100]), node_name="guidance_hand_green")

if kps is not None:
    for name, idx in finger_ids.items():
        p = kps[idx]
        d_screen, j_screen = screen_tree.query(p, k=1)
        d_base, j_base = base_tree.query(p, k=1)

        contacts[name] = {
            "kps_index": idx,
            "point": p.tolist(),
            "distance_to_screen": float(d_screen),
            "nearest_screen_point": screen_pts[j_screen].tolist(),
            "distance_to_keyboard_base": float(d_base),
            "nearest_base_point": base_pts[j_base].tolist(),
            "primary_part": "screen" if d_screen <= d_base else "keyboard_base",
            "screen_contact_lite": bool(d_screen <= 0.03)
        }

        scene.add_geometry(marker(p, 0.006, [255, 0, 0, 255]), node_name=f"{name}_red")
        scene.add_geometry(marker(screen_pts[j_screen], 0.005, [0, 0, 255, 255]), node_name=f"{name}_nearest_screen_blue")
else:
    # Fallback: global hand-to-screen distance only.
    hand_pts = np.asarray(hand.vertices)
    d, idx = screen_tree.query(hand_pts, k=1)
    contacts["fallback_global_hand_to_screen"] = {
        "min": float(d.min()),
        "p1": float(np.percentile(d, 1)),
        "p5": float(np.percentile(d, 5)),
        "mean": float(d.mean()),
        "note": "HaMeR keypoints were not parsed; use global hand-screen distance only."
    }

result = {
    "case_id": "alapuse01",
    "stage": "Gate C v3-lite contact verification",
    "object_seed": "v0 dry-run active clean parts, not v0.1 optimized output",
    "contact_hypothesis": [
        "right index -> screen / outer_top_lid",
        "right middle -> screen / outer_top_lid",
        "right ring -> screen / outer_top_lid"
    ],
    "kps_available": kps is not None,
    "contacts": contacts,
    "decision_rule": {
        "pass": "at least one intended finger is within about 3cm of screen and visual marker is plausible",
        "partial": "finger is near screen but markers suggest wrong region or occlusion uncertainty",
        "fail": "all intended fingers are far from screen"
    }
}

out_json = OUT_METRICS / "gate_c_v3_lite_contact_check.json"
out_glb = OUT_VIS / "gate_c_v3_lite_contact_markers.glb"
out_json.write_text(json.dumps(result, indent=2))
scene.export(out_glb)

print("[OK] wrote", out_json)
print("[OK] wrote", out_glb)
print(json.dumps(result, indent=2)[:3000])
