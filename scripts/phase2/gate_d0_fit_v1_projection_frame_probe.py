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

part_dir = resolve(m["active_parts_dir"])

transforms = {
    "identity_xyz": lambda v: v,
    "flip_y": lambda v: np.stack([v[:,0], -v[:,1], v[:,2]], axis=1),
    "flip_z": lambda v: np.stack([v[:,0], v[:,1], -v[:,2]], axis=1),
    "flip_yz": lambda v: np.stack([v[:,0], -v[:,1], -v[:,2]], axis=1),
    "swap_yz": lambda v: np.stack([v[:,0], v[:,2], v[:,1]], axis=1),
    "swap_yz_flip_z": lambda v: np.stack([v[:,0], v[:,2], -v[:,1]], axis=1),
    "swap_yz_flip_y": lambda v: np.stack([v[:,0], -v[:,2], v[:,1]], axis=1),
    "swap_xz": lambda v: np.stack([v[:,2], v[:,1], v[:,0]], axis=1),
    "swap_xz_flip_z": lambda v: np.stack([v[:,2], v[:,1], -v[:,0]], axis=1)
}

def project(v):
    z = v[:, 2]
    valid_z = z > 1e-6
    z_safe = np.clip(z, 1e-6, None)

    u = np.round(K[0, 0] * v[:, 0] / z_safe + K[0, 2]).astype(int)
    y = np.round(K[1, 1] * v[:, 1] / z_safe + K[1, 2]).astype(int)

    valid = valid_z & (u >= 0) & (u < W) & (y >= 0) & (y < H)
    return u, y, valid

def component_stats(mesh, transform_name):
    v0 = np.asarray(mesh.vertices, dtype=float)
    v = transforms[transform_name](v0)

    u, y, valid = project(v)
    out = {
        "num_vertices": int(len(v)),
        "valid_projected_vertices": int(valid.sum()),
        "valid_ratio": float(valid.mean()) if len(v) else 0.0,
        "z_min": float(np.min(v[:,2])) if len(v) else None,
        "z_max": float(np.max(v[:,2])) if len(v) else None
    }

    if valid.sum() > 0:
        uu, yy = u[valid], y[valid]
        out.update({
            "u_min": int(uu.min()),
            "u_max": int(uu.max()),
            "y_min": int(yy.min()),
            "y_max": int(yy.max()),
            "obj_score": float(mask_obj[yy, uu].mean()),
            "lid_score": float(mask_lid[yy, uu].mean()),
            "base_score": float(mask_base[yy, uu].mean())
        })
    else:
        out.update({
            "obj_score": 0.0,
            "lid_score": 0.0,
            "base_score": 0.0
        })

    return out

report = {}
summary = []

for tname in transforms:
    report[tname] = {}
    total_valid = 0
    total_obj = []
    total_lid = []
    total_base = []

    for part_name in ["screen.ply", "keyboard_base.ply", "hinge.ply"]:
        p = part_dir / part_name
        if not p.exists():
            continue

        mesh = trimesh.load(p, force="mesh", process=False)
        comps = list(mesh.split(only_watertight=False))
        report[tname][part_name] = {}

        for i, comp in enumerate(comps):
            if len(comp.vertices) == 0:
                continue

            stats = component_stats(comp, tname)
            report[tname][part_name][f"component_{i:02d}"] = stats

            total_valid += stats["valid_projected_vertices"]
            total_obj.append(stats["obj_score"])
            total_lid.append(stats["lid_score"])
            total_base.append(stats["base_score"])

    score = (
        1.0 * np.mean(total_obj) if total_obj else 0.0
    ) + (
        0.5 * max(np.mean(total_lid) if total_lid else 0.0,
                  np.mean(total_base) if total_base else 0.0)
    ) + (
        min(total_valid / 1000.0, 1.0)
    )

    summary.append({
        "transform": tname,
        "score": float(score),
        "total_valid_projected_vertices": int(total_valid),
        "mean_obj_score": float(np.mean(total_obj)) if total_obj else 0.0,
        "mean_lid_score": float(np.mean(total_lid)) if total_lid else 0.0,
        "mean_base_score": float(np.mean(total_base)) if total_base else 0.0
    })

summary = sorted(summary, key=lambda x: x["score"], reverse=True)

out = {
    "case_id": "alapuse01",
    "stage": "projection_frame_probe",
    "camera": m["camera"],
    "summary_ranked": summary,
    "details": report,
    "recommended_transform": summary[0]["transform"] if summary else None
}

out_json = FIT / "metrics/projection_frame_probe.json"
out_json.write_text(json.dumps(out, indent=2))

print("[OK] wrote", out_json)
print("[recommended_transform]", out["recommended_transform"])
print(json.dumps(summary[:10], indent=2))
