from pathlib import Path
import json
import sys
import numpy as np

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit_v1_getting_unstuck"
MAN = FIT / "inputs/fit_input_manifest.json"

m = json.loads(MAN.read_text())

def resolve(p):
    p = Path(p)
    return p if p.is_absolute() else CASE_ROOT / p

status = {}
ok = True

required = [
    "image_rgb",
    "mask_object",
    "mask_lid",
    "mask_base",
    "depth_metric_npy",
    "hand_mesh",
    "contact_prior"
]

for key in required:
    p = resolve(m[key])
    exists = p.exists() and "TODO" not in str(p)
    status[key] = {"path": str(p), "ok": bool(exists)}
    ok = ok and exists

parts_dir = resolve(m["active_parts_dir"])
for part in ["screen.ply", "keyboard_base.ply", "hinge.ply"]:
    p = parts_dir / part
    exists = p.exists()
    status[f"part:{part}"] = {"path": str(p), "ok": bool(exists)}
    ok = ok and exists

if status["depth_metric_npy"]["ok"]:
    d = np.load(resolve(m["depth_metric_npy"]))
    finite = np.isfinite(d)
    status["depth_stats"] = {
        "shape": list(d.shape),
        "finite_ratio": float(finite.mean()),
        "min": float(np.nanmin(d)),
        "max": float(np.nanmax(d)),
        "mean": float(np.nanmean(d))
    }
    if np.nanmax(d) > 20:
        status["depth_stats"]["warning"] = "depth max > 20; check whether units are meters"

out = FIT / "metrics/fit_v1_input_audit.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(status, indent=2))

print(json.dumps(status, indent=2))
print("[AUDIT]", "ALL_INPUTS_OK" if ok else "MISSING_INPUTS_FIX_MANIFEST_FIRST")
sys.exit(0 if ok else 1)
