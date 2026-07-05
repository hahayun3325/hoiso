from pathlib import Path
import json
import numpy as np
import trimesh

DATA = Path("/home/fredcui/foho_phase0")
CASE = "alapuse02_v3b"
TOKEN = "alapuse02v3b"

RUN = DATA / "phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse02_v3b_selector_v41_refined_pipeline"
CASE_ROOT = DATA / "phase2_gateA_part_recon/cases" / CASE
OUT = CASE_ROOT / "integrated_gates/gate_a0_hunyuan_frame_sanity"
VIS = OUT / "visuals"
MET = OUT / "metrics"
VIS.mkdir(parents=True, exist_ok=True)
MET.mkdir(parents=True, exist_ok=True)

paths = {
    "hunyuan_raw": RUN / "hunyuan_hoi_out" / f"{TOKEN}_hoi_mesh.ply",
    "guidance_hand": RUN / "guidance_out" / f"{TOKEN}_hand.ply",
    "guidance_object": RUN / "guidance_out" / f"{TOKEN}_obj.ply",
    "aligned_mano": RUN / "aligned_mano" / f"{TOKEN}_hamer_aligned_mano.ply",
    "h2m": RUN / "h2m_transformations" / f"{TOKEN}_hoi_mesh.npy",
    "moge_mesh": RUN / "moge_out" / f"{TOKEN}_cropped_hoi" / "mesh.glb",
    "moge_pc": RUN / "moge_out" / f"{TOKEN}_cropped_hoi" / "pointcloud.ply",
}

missing = [k for k, p in paths.items() if not p.exists()]
if missing:
    raise SystemExit(f"[FAIL] missing inputs: {missing}")

def load_mesh(path):
    obj = trimesh.load(path, process=False)
    if isinstance(obj, trimesh.Scene):
        geoms = [g for g in obj.geometry.values() if hasattr(g, "vertices") and len(g.vertices) > 0]
        if not geoms:
            raise ValueError(f"empty scene: {path}")
        obj = trimesh.util.concatenate(geoms)
    return obj

def colorize(mesh, rgba):
    m = mesh.copy()
    m.visual = trimesh.visual.ColorVisuals(m, vertex_colors=np.tile(np.array(rgba, dtype=np.uint8), (len(m.vertices), 1)))
    return m

def stats(mesh):
    b = mesh.bounds
    return {
        "vertices": int(len(mesh.vertices)),
        "faces": int(len(mesh.faces)) if hasattr(mesh, "faces") else 0,
        "bbox_min": b[0].tolist(),
        "bbox_max": b[1].tolist(),
        "bbox_extent": (b[1] - b[0]).tolist(),
        "bbox_center": ((b[0] + b[1]) / 2).tolist()
    }

def sample_points(mesh, n=5000):
    if hasattr(mesh, "faces") and len(mesh.faces) > 0:
        return trimesh.sample.sample_surface(mesh, min(n, max(1, len(mesh.faces))))[0]
    v = np.asarray(mesh.vertices)
    if len(v) <= n:
        return v
    idx = np.random.choice(len(v), n, replace=False)
    return v[idx]

def nn_summary(src, tgt, n=5000):
    from scipy.spatial import cKDTree
    a = sample_points(src, n)
    b = sample_points(tgt, n)
    d, _ = cKDTree(b).query(a)
    return {
        "min": float(np.min(d)),
        "p1": float(np.percentile(d, 1)),
        "p5": float(np.percentile(d, 5)),
        "p10": float(np.percentile(d, 10)),
        "mean": float(np.mean(d)),
        "within_01": int((d < 0.01).sum()),
        "within_02": int((d < 0.02).sum()),
        "within_05": int((d < 0.05).sum())
    }

hunyuan = load_mesh(paths["hunyuan_raw"])
hand = load_mesh(paths["guidance_hand"])
gobj = load_mesh(paths["guidance_object"])
aligned = load_mesh(paths["aligned_mano"])
moge = load_mesh(paths["moge_mesh"] if paths["moge_mesh"].exists() else paths["moge_pc"])

T = np.load(paths["h2m"])
hunyuan_h2m = hunyuan.copy()
hunyuan_h2m.apply_transform(T)

scene = trimesh.Scene()
scene.add_geometry(colorize(hunyuan, [0, 160, 255, 45]), node_name="raw_hunyuan_blue")
scene.add_geometry(colorize(hunyuan_h2m, [160, 0, 255, 65]), node_name="h2m_hunyuan_purple")
scene.add_geometry(colorize(moge, [0, 255, 255, 35]), node_name="moge_target_cyan")
scene.add_geometry(colorize(gobj, [255, 255, 255, 180]), node_name="guidance_object_white")
scene.add_geometry(colorize(hand, [0, 255, 0, 180]), node_name="guidance_hand_green")
scene.add_geometry(colorize(aligned, [120, 120, 120, 90]), node_name="aligned_mano_gray")

scene_path = VIS / f"{CASE}_gate_a0_hunyuan_frame_sanity.glb"
scene.export(scene_path)

report = {
    "case": CASE,
    "token": TOKEN,
    "paths": {k: str(v) for k, v in paths.items()},
    "mesh_stats": {
        "raw_hunyuan": stats(hunyuan),
        "h2m_hunyuan": stats(hunyuan_h2m),
        "moge_target": stats(moge),
        "guidance_object": stats(gobj),
        "guidance_hand": stats(hand),
        "aligned_mano": stats(aligned),
    },
    "distances": {
        "h2m_hunyuan_to_moge": nn_summary(hunyuan_h2m, moge),
        "guidance_object_to_h2m_hunyuan": nn_summary(gobj, hunyuan_h2m),
        "guidance_hand_to_guidance_object": nn_summary(hand, gobj),
        "guidance_hand_to_h2m_hunyuan": nn_summary(hand, hunyuan_h2m),
    },
    "decision_hint": "inspect scene and compare h2m_hunyuan vs guidance_object"
}

report_path = MET / f"{CASE}_gate_a0_hunyuan_frame_sanity_report.json"
report_path.write_text(json.dumps(report, indent=2))

print("[OK] scene:", scene_path)
print("[OK] report:", report_path)
print(json.dumps(report["distances"], indent=2))
