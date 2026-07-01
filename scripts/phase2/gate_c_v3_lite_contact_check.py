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


def to_numpy_safe(x):
    """Convert torch CUDA/CPU tensor, numpy array, scalar, or list to numpy safely."""
    if hasattr(x, "detach"):
        x = x.detach()
    if hasattr(x, "cpu"):
        x = x.cpu()
    if hasattr(x, "numpy"):
        return x.numpy()
    return np.asarray(x)


def load_mesh(path):
    obj = trimesh.load(path, force=None, process=False)
    if isinstance(obj, trimesh.Scene):
        geoms = [
            g for g in obj.geometry.values()
            if hasattr(g, "vertices") and len(g.vertices) > 0
        ]
        if not geoms:
            raise ValueError(f"empty scene: {path}")
        return trimesh.util.concatenate(geoms)
    return obj


def colorize(mesh, rgba):
    m = mesh.copy()
    m.visual.vertex_colors = rgba
    return m


def marker(center, radius, rgba):
    center = np.asarray(center, dtype=float).reshape(3)
    s = trimesh.creation.icosphere(subdivisions=2, radius=radius)
    s.apply_translation(center)
    s.visual.vertex_colors = rgba
    return s


def find_21x3_keypoints(obj):
    """
    Search a loaded .npy/.pkl-like object for a 21x3 or Nx3 keypoint array.
    Handles dicts, lists, tuples, numpy arrays, and torch tensors.
    """
    candidates = []

    def visit(x, name="root"):
        if x is None:
            return

        if isinstance(x, dict):
            for k, v in x.items():
                visit(v, f"{name}.{k}")
            return

        if isinstance(x, (list, tuple)):
            for i, v in enumerate(x):
                visit(v, f"{name}[{i}]")
            return

        try:
            arr = to_numpy_safe(x)
        except Exception:
            return

        arr = np.asarray(arr)

        if arr.dtype == object:
            # Object arrays may wrap dicts/tensors.
            if arr.shape == ():
                visit(arr.item(), name + ".item")
            else:
                for i, v in enumerate(arr.reshape(-1)):
                    visit(v, f"{name}.obj{i}")
            return

        if arr.ndim >= 2 and arr.shape[-1] == 3:
            flat = arr.reshape(-1, 3)
            if flat.shape[0] >= 21:
                candidates.append({
                    "name": name,
                    "array": flat[:21].astype(float),
                    "raw_shape": list(arr.shape),
                    "num_points": int(flat.shape[0])
                })

    visit(obj)

    if not candidates:
        return None, []

    # Prefer exactly 21 joints if present; otherwise first plausible candidate.
    candidates_sorted = sorted(candidates, key=lambda c: (abs(c["num_points"] - 21), c["name"]))
    return candidates_sorted[0], candidates_sorted


def hand_vertices_near_screen(hand, screen, percentile_list=(1, 5, 10)):
    hand_pts = np.asarray(hand.vertices, dtype=float)
    screen_pts = np.asarray(screen.vertices, dtype=float)
    tree = cKDTree(screen_pts)
    d, idx = tree.query(hand_pts, k=1)

    out = {
        "min": float(d.min()),
        "mean": float(d.mean()),
        "nearest_hand_vertex_index": int(np.argmin(d)),
        "nearest_hand_vertex": hand_pts[int(np.argmin(d))].tolist(),
        "nearest_screen_point": screen_pts[idx[int(np.argmin(d))]].tolist(),
    }
    for p in percentile_list:
        out[f"p{p}"] = float(np.percentile(d, p))
    return out


data = json.loads(MANIFEST.read_text())
paths = {k: Path(v["path"]) for k, v in data["paths"].items() if v["exists"]}

screen = load_mesh(ACTIVE / "screen.ply")
base = load_mesh(ACTIVE / "keyboard_base.ply")
hinge = load_mesh(ACTIVE / "hinge.ply")
hand = load_mesh(paths["guidance_hand"])

screen_pts = np.asarray(screen.vertices, dtype=float)
base_pts = np.asarray(base.vertices, dtype=float)
screen_tree = cKDTree(screen_pts)
base_tree = cKDTree(base_pts)

scene = trimesh.Scene()
scene.add_geometry(colorize(screen, [0, 0, 255, 150]), node_name="active_screen_blue")
scene.add_geometry(colorize(base, [255, 140, 0, 180]), node_name="active_keyboard_base_orange")
scene.add_geometry(colorize(hinge, [255, 0, 255, 220]), node_name="active_hinge_magenta")
scene.add_geometry(colorize(hand, [0, 255, 0, 100]), node_name="guidance_hand_green")

# Try to parse HaMeR keypoints.
kps = None
kps_source = None
candidate_summary = []

kps_path = paths.get("hamer_kps", None)
if kps_path and kps_path.exists():
    raw = np.load(kps_path, allow_pickle=True)
    chosen, candidates = find_21x3_keypoints(raw)
    candidate_summary = [
        {
            "name": c["name"],
            "raw_shape": c["raw_shape"],
            "num_points": c["num_points"]
        }
        for c in candidates[:20]
    ]
    if chosen is not None:
        kps = chosen["array"]
        kps_source = chosen["name"]

contacts = {}
finger_ids = {
    "index_tip": 8,
    "middle_tip": 12,
    "ring_tip": 16
}

if kps is not None:
    for name, idx in finger_ids.items():
        p = np.asarray(kps[idx], dtype=float)

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
            "screen_contact_lite_3cm": bool(d_screen <= 0.03),
            "screen_contact_lite_5cm": bool(d_screen <= 0.05)
        }

        scene.add_geometry(marker(p, 0.006, [255, 0, 0, 255]), node_name=f"{name}_red_kp")
        scene.add_geometry(marker(screen_pts[j_screen], 0.005, [0, 0, 255, 255]), node_name=f"{name}_nearest_screen_blue")
else:
    contacts["fallback_global_hand_to_screen"] = hand_vertices_near_screen(hand, screen)

# Always include global hand-screen distance as a sanity check.
global_hand_screen = hand_vertices_near_screen(hand, screen)

# Simple decision.
if kps is not None:
    intended = [contacts[k]["distance_to_screen"] for k in finger_ids.keys()]
    best_d = min(intended)
    num_under_3cm = sum(d <= 0.03 for d in intended)
    num_under_5cm = sum(d <= 0.05 for d in intended)

    if num_under_3cm >= 1:
        decision = "PASS_LITE_AT_LEAST_ONE_FINGER_WITHIN_3CM_OF_SCREEN"
    elif num_under_5cm >= 1:
        decision = "PARTIAL_PASS_LITE_AT_LEAST_ONE_FINGER_WITHIN_5CM_OF_SCREEN"
    else:
        decision = "FAIL_LITE_INTENDED_FINGERS_FAR_FROM_SCREEN"
else:
    best_d = global_hand_screen["min"]
    if global_hand_screen["p1"] <= 0.03:
        decision = "PARTIAL_PASS_GLOBAL_HAND_SCREEN_NEAR_BUT_NO_KEYPOINTS"
    else:
        decision = "FAIL_GLOBAL_HAND_SCREEN_FAR_NO_KEYPOINTS"

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
    "kps_source": kps_source,
    "kps_candidates_seen": candidate_summary,
    "contacts": contacts,
    "global_hand_to_screen": global_hand_screen,
    "decision": decision,
    "decision_rule": {
        "pass": "at least one intended fingertip is within about 3cm of screen and visual marker is plausible",
        "partial": "at least one intended fingertip is within about 5cm, or global hand-screen near without keypoints",
        "fail": "all intended fingertips are far from screen"
    },
    "next_step_hint": "Open the marker GLB and verify whether red fingertip markers are on the intended hand/fingers."
}

out_json = OUT_METRICS / "gate_c_v3_lite_contact_check.json"
out_glb = OUT_VIS / "gate_c_v3_lite_contact_markers.glb"

out_json.write_text(json.dumps(result, indent=2))
scene.export(out_glb)

print("[OK] wrote", out_json)
print("[OK] wrote", out_glb)
print("[DECISION]", decision)
print(json.dumps(result, indent=2)[:4000])
