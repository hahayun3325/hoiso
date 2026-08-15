from pathlib import Path
import json
import sys
from PIL import Image

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
    "hand_mesh",
    "contact_prior"
]

for key in required:
    p = resolve(m[key])
    exists = p.exists() and "TODO" not in str(p) and "MISSING" not in str(p)
    status[key] = {"path": str(p), "ok": bool(exists)}
    ok = ok and exists

parts_dir = resolve(m["active_parts_dir"])
for part in ["screen.ply", "keyboard_base.ply", "hinge.ply"]:
    p = parts_dir / part
    exists = p.exists()
    status[f"part:{part}"] = {"path": str(p), "ok": bool(exists)}
    ok = ok and exists

# Camera must be real.
cam = m.get("camera", {})
camera_ok = "TODO" not in cam and "source" in cam
status["camera"] = {
    "ok": bool(camera_ok),
    "width": cam.get("width"),
    "height": cam.get("height"),
    "source": cam.get("source")
}
ok = ok and camera_ok

# Basic image-size consistency.
if status["mask_lid"]["ok"] and status["mask_base"]["ok"]:
    lid_size = Image.open(resolve(m["mask_lid"])).size
    base_size = Image.open(resolve(m["mask_base"])).size
    status["mask_sizes"] = {
        "lid": list(lid_size),
        "base": list(base_size),
        "camera_wh": [cam.get("width"), cam.get("height")],
        "ok": lid_size == base_size == (cam.get("width"), cam.get("height"))
    }
    ok = ok and status["mask_sizes"]["ok"]

out = FIT / "metrics/fit_v1_relabel_input_audit.json"
out.write_text(json.dumps(status, indent=2))

print(json.dumps(status, indent=2))
print("[RELABEL_AUDIT]", "ALL_RELABEL_INPUTS_OK" if ok else "MISSING_RELABEL_INPUTS")
sys.exit(0 if ok else 1)
