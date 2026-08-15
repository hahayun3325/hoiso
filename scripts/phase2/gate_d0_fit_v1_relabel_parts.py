from pathlib import Path
import json
import numpy as np
import trimesh
from PIL import Image

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit_v1_getting_unstuck"
MAN = FIT / "inputs/fit_input_manifest.json"
m = json.loads(MAN.read_text())

def resolve(p):
    p = Path(p)
    return p if p.is_absolute() else CASE_ROOT / p

K = np.asarray(m["camera"]["K"], dtype=float)
W = int(m["camera"]["width"])
H = int(m["camera"]["height"])

mask_obj = np.asarray(Image.open(resolve(m["mask_object"])).convert("L")) > 127
mask_lid = np.asarray(Image.open(resolve(m["mask_lid"])).convert("L")) > 127
mask_base = np.asarray(Image.open(resolve(m["mask_base"])).convert("L")) > 127

def project_vertices(v):
    v = np.asarray(v, dtype=float)
    z = v[:, 2]
    valid_z = z > 1e-6
    z_safe = np.clip(z, 1e-6, None)

    u = np.round(K[0, 0] * v[:, 0] / z_safe + K[0, 2]).astype(int)
    y = np.round(K[1, 1] * v[:, 1] / z_safe + K[1, 2]).astype(int)

    valid = (
        valid_z
        & (u >= 0) & (u < W)
        & (y >= 0) & (y < H)
    )
    return u, y, valid

def vote_component(mesh):
    u, y, valid = project_vertices(mesh.vertices)
    if valid.sum() < 10:
        return "discard", {"reason": "not_enough_visible_vertices", "valid_vertices": int(valid.sum())}

    u = u[valid]
    y = y[valid]

    in_obj = float(mask_obj[y, u].mean())
    lid_score = float(mask_lid[y, u].mean())
    base_score = float(mask_base[y, u].mean())

    if in_obj < 0.30:
        return "discard", {
            "reason": "outside_object_mask",
            "in_obj": in_obj,
            "lid_score": lid_score,
            "base_score": base_score
        }

    label = "lid" if lid_score >= base_score else "base"
    return label, {
        "in_obj": in_obj,
        "lid_score": lid_score,
        "base_score": base_score
    }

active_dir = resolve(m["active_parts_dir"])
out_dir = FIT / "outputs"
vis_dir = FIT / "visuals"
metrics_dir = FIT / "metrics"

for p in [out_dir, vis_dir, metrics_dir]:
    p.mkdir(parents=True, exist_ok=True)

buckets = {"lid": [], "base": []}
report = {}

for source_name in ["screen.ply", "keyboard_base.ply", "hinge.ply"]:
    path = active_dir / source_name
    if not path.exists():
        continue

    mesh = trimesh.load(path, force="mesh", process=False)
    comps = list(mesh.split(only_watertight=False))

    for i, comp in enumerate(comps):
        if len(comp.faces) < 50:
            report[f"{source_name}#component_{i}"] = {
                "label": "discard",
                "reason": "tiny_component",
                "faces": int(len(comp.faces))
            }
            continue

        label, info = vote_component(comp)
        report[f"{source_name}#component_{i}"] = {
            "label": label,
            "faces": int(len(comp.faces)),
            "vertices": int(len(comp.vertices)),
            "area": float(comp.area),
            **info
        }

        if label in buckets:
            buckets[label].append(comp)

result = {}

for label, comps in buckets.items():
    if not comps:
        result[label] = {"exists": False, "error": "no components selected"}
        continue

    merged = trimesh.util.concatenate(comps)
    merged_components = list(merged.split(only_watertight=False))
    largest = max(merged_components, key=lambda x: x.area)

    out_path = out_dir / f"{label}_relabel_v1.ply"
    largest.export(out_path)

    result[label] = {
        "exists": True,
        "output": str(out_path),
        "components_merged": int(len(comps)),
        "merged_components_after": int(len(merged_components)),
        "kept_faces": int(len(largest.faces)),
        "kept_vertices": int(len(largest.vertices)),
        "kept_area_ratio": float(largest.area / max(merged.area, 1e-9)),
        "bbox_extent_xyz": (largest.bounds[1] - largest.bounds[0]).tolist()
    }

# Visual scene
scene = trimesh.Scene()
colors = {
    "lid": [0, 220, 220, 180],
    "base": [255, 0, 255, 180]
}
for label in ["lid", "base"]:
    p = out_dir / f"{label}_relabel_v1.ply"
    if p.exists():
        mesh = trimesh.load(p, force="mesh", process=False)
        mesh.visual.vertex_colors = colors[label]
        scene.add_geometry(mesh, node_name=f"{label}_relabel_v1")

scene_path = vis_dir / "relabel_v1_scene.glb"
scene.export(scene_path)

out_json = metrics_dir / "relabel_v1_report.json"
out_json.write_text(json.dumps({"per_component": report, "result": result}, indent=2))

print("[OK] wrote", out_json)
print("[OK] wrote", scene_path)
print(json.dumps(result, indent=2))
