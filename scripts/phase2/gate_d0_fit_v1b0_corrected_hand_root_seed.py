from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit_v1_getting_unstuck"
V1A7 = FIT / "corrected_scale_root_pose_probe_v1a7"
V1B0 = FIT / "v1b0_corrected_hand_root_seed"

SEL_RUN = Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse01_selector_v41_refined_pipeline")

VIS = V1B0 / "visuals"
MET = V1B0 / "metrics"
OUT = V1B0 / "outputs"
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

def translate(mesh, vec):
    m = mesh.copy()
    m.apply_translation(np.asarray(vec, dtype=float))
    return m

def bbox(mesh):
    b = np.asarray(mesh.bounds, dtype=float)
    e = b[1] - b[0]
    return {
        "center": np.asarray(mesh.centroid).tolist(),
        "bbox_min": b[0].tolist(),
        "bbox_max": b[1].tolist(),
        "extent_xyz": e.tolist(),
        "xy_max_extent": float(e[:2].max()),
        "max_extent": float(e.max()),
        "num_vertices": int(len(mesh.vertices)),
        "num_faces": int(len(mesh.faces))
    }

def sample(mesh, n=12000, seed=0):
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
    d, idx = tree.query(A, k=1)
    return d, idx, {
        "min": float(np.min(d)),
        "p1": float(np.percentile(d, 1)),
        "p5": float(np.percentile(d, 5)),
        "p10": float(np.percentile(d, 10)),
        "mean": float(np.mean(d)),
        "within_02": int(np.sum(d < 0.02)),
        "within_05": int(np.sum(d < 0.05))
    }

def make_spheres(points, radius=0.006, rgba=(255,0,0,255), max_points=80):
    geoms = []
    pts = np.asarray(points)
    if len(pts) > max_points:
        pts = pts[np.linspace(0, len(pts)-1, max_points).astype(int)]
    for p in pts:
        s = trimesh.creation.uv_sphere(radius=radius)
        s.apply_translation(p)
        s.visual.vertex_colors = rgba
        geoms.append(s)
    return geoms

def export_scene(name, hand, screen, base, hinge, extra_geoms=None):
    scene = trimesh.Scene()
    scene.add_geometry(colorize(hand, [0, 255, 0, 130]), node_name="hand_v1b0_green")
    scene.add_geometry(colorize(screen, [0, 190, 255, 145]), node_name="screen_lid_cyan")
    scene.add_geometry(colorize(base, [255, 0, 255, 145]), node_name="base_magenta")
    scene.add_geometry(colorize(hinge, [255, 180, 0, 180]), node_name="hinge_yellow")
    if extra_geoms:
        for i, g in enumerate(extra_geoms):
            scene.add_geometry(g, node_name=f"marker_{i:03d}")
    out = VIS / f"{name}.glb"
    scene.export(out)
    return str(out)

# Load corrected-scale hand/object from v1a7.
hand_scaled = load_mesh(V1A7 / "outputs/hand_aligned_mano_scaled_to_guidance_bbox_v1a7.ply")
screen_scaled = load_mesh(V1A7 / "outputs/screen_object_scaled_v1a7.ply")
base_scaled = load_mesh(V1A7 / "outputs/base_object_scaled_v1a7.ply")
hinge_scaled = load_mesh(V1A7 / "outputs/hinge_object_scaled_v1a7.ply")

# Load guidance hand for root translation only.
guidance_hand = load_mesh(SEL_RUN / "guidance_out/alapuse01_hand.ply")

# Re-root corrected hand to guidance hand center.
delta_hand_root = np.asarray(guidance_hand.centroid) - np.asarray(hand_scaled.centroid)
hand_v1b0 = translate(hand_scaled, delta_hand_root)

# Use object as-is from corrected v1a7 object scale.
screen_v1b0 = screen_scaled.copy()
base_v1b0 = base_scaled.copy()
hinge_v1b0 = hinge_scaled.copy()

# Optional relabeled lid/base from image evidence.
# These are only used for semantic audit if found.
candidate_lid_files = sorted(FIT.rglob("lid_relabel_v1.ply"))
candidate_base_files = sorted(FIT.rglob("base_relabel_v1.ply"))
lid_sem = load_mesh(candidate_lid_files[0]) if candidate_lid_files else screen_v1b0
base_sem = load_mesh(candidate_base_files[0]) if candidate_base_files else base_v1b0

# Distance audit.
hand_v = np.asarray(hand_v1b0.vertices)
screen_pts = sample(screen_v1b0, 12000, seed=1)
base_pts = sample(base_v1b0, 12000, seed=2)
lid_sem_pts = sample(lid_sem, 12000, seed=3)
base_sem_pts = sample(base_sem, 12000, seed=4)

d_screen, idx_screen, hand_to_screen = nearest_stats(hand_v, screen_pts)
d_base, idx_base, hand_to_base = nearest_stats(hand_v, base_pts)
d_lid_sem, idx_lid_sem, hand_to_lid_sem = nearest_stats(hand_v, lid_sem_pts)
d_base_sem, idx_base_sem, hand_to_base_sem = nearest_stats(hand_v, base_sem_pts)

# Mark closest hand vertices to semantic lid and base.
k = min(80, max(20, int(0.05 * len(hand_v))))
lid_ids = np.argsort(d_lid_sem)[:k]
base_ids = np.argsort(d_base_sem)[:k]

lid_markers = make_spheres(hand_v[lid_ids], radius=0.006, rgba=(0,0,255,255), max_points=80)
base_markers = make_spheres(hand_v[base_ids], radius=0.006, rgba=(255,0,0,255), max_points=80)

scene_seed = export_scene(
    "v1b0_corrected_hand_root_seed",
    hand_v1b0, screen_v1b0, base_v1b0, hinge_v1b0
)

scene_audit = export_scene(
    "v1b0_semantic_contact_audit_blue_lid_red_base",
    hand_v1b0, screen_v1b0, base_v1b0, hinge_v1b0,
    extra_geoms=lid_markers + base_markers
)

# Export meshes.
hand_v1b0.export(OUT / "hand_v1b0_scaled_aligned_mano_guidance_root.ply")
screen_v1b0.export(OUT / "screen_v1b0_object_scaled.ply")
base_v1b0.export(OUT / "base_v1b0_object_scaled.ply")
hinge_v1b0.export(OUT / "hinge_v1b0_object_scaled.ply")

# Conservative decision.
# This is intentionally not final; visual audit is required because earlier numeric screen distance was misleading.
decision = "VISUAL_CHECK_REQUIRED"
if hand_to_lid_sem["within_05"] > 50 and hand_to_base_sem["within_05"] < 20:
    decision = "V1B0_NUMERIC_LID_CONTACT_POSSIBLE_VISUAL_CHECK_REQUIRED"
elif hand_to_base_sem["within_05"] >= hand_to_lid_sem["within_05"]:
    decision = "V1B0_SEMANTIC_RISK_BASE_CONTACT_DOMINATES"
else:
    decision = "V1B0_PARTIAL_LID_CONTACT_BUT_VISUAL_CHECK_REQUIRED"

report = {
    "case_id": "alapuse01",
    "stage": "Gate D-0 fit v1b0 corrected hand-root seed",
    "uses_gt": False,
    "construction": {
        "hand": "v1a7 scaled aligned_mano shape re-rooted to guidance_hand centroid",
        "object": "v1a7 corrected-scale object, no extra object-root correction",
        "semantic_lid_source": str(candidate_lid_files[0]) if candidate_lid_files else "fallback_screen_v1b0",
        "semantic_base_source": str(candidate_base_files[0]) if candidate_base_files else "fallback_base_v1b0"
    },
    "delta_hand_root_to_guidance": {
        "vec": delta_hand_root.tolist(),
        "norm": float(np.linalg.norm(delta_hand_root))
    },
    "metrics": {
        "hand_to_screen_active": hand_to_screen,
        "hand_to_base_active": hand_to_base,
        "hand_to_lid_semantic": hand_to_lid_sem,
        "hand_to_base_semantic": hand_to_base_sem
    },
    "mesh_bboxes": {
        "hand_v1b0": bbox(hand_v1b0),
        "screen_v1b0": bbox(screen_v1b0),
        "base_v1b0": bbox(base_v1b0),
        "hinge_v1b0": bbox(hinge_v1b0),
        "lid_semantic": bbox(lid_sem),
        "base_semantic": bbox(base_sem)
    },
    "visuals": {
        "seed_scene": scene_seed,
        "semantic_contact_audit_scene": scene_audit
    },
    "outputs": {
        "hand_v1b0": str(OUT / "hand_v1b0_scaled_aligned_mano_guidance_root.ply"),
        "screen_v1b0": str(OUT / "screen_v1b0_object_scaled.ply"),
        "base_v1b0": str(OUT / "base_v1b0_object_scaled.ply"),
        "hinge_v1b0": str(OUT / "hinge_v1b0_object_scaled.ply")
    },
    "decision": decision,
    "decision_rule": {
        "PASS_TO_V1B1": "visual contact is on lid/screen and base penetration is small",
        "SEMANTIC_FAIL": "visual contact still lands on keyboard/base",
        "PARTIAL": "root/scale is improved but residual semantic contact is wrong"
    },
    "next_step": "inspect v1b0 scenes; if contact is on lid, create v1b1 small residual fitter; if base contact remains, create lid-targeted residual correction"
}

out = MET / "fit_v1b0_corrected_hand_root_seed.json"
out.write_text(json.dumps(report, indent=2))

print("[OK] wrote", out)
print("[decision]", decision)
print("[delta_hand_root_norm]", report["delta_hand_root_to_guidance"]["norm"])
print("[metrics]")
print(json.dumps(report["metrics"], indent=2))
print("[visuals]")
for k, v in report["visuals"].items():
    print(k, "->", v)
