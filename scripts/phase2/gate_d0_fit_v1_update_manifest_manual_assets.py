from pathlib import Path
import json

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit_v1_getting_unstuck"
MAN = FIT / "inputs/fit_input_manifest.json"

m = json.loads(MAN.read_text())

cam_meta_path = FIT / "inputs/alapuse01_moge_camera_from_fov.json"
lid_mask = FIT / "inputs/alapuse01_lid_mask_manual_v1.png"
base_mask = FIT / "inputs/alapuse01_base_mask_manual_v1.png"
depth_npy = FIT / "inputs/alapuse01_moge_metric_depth.npy"

for p in [cam_meta_path, lid_mask, base_mask]:
    if not p.exists():
        raise FileNotFoundError(p)

cam = json.loads(cam_meta_path.read_text())

m["camera"]["K"] = cam["K"]
m["camera"]["width"] = cam["width"]
m["camera"]["height"] = cam["height"]
m["camera"]["source"] = "moge fov.json converted to pinhole K"
m["camera"].pop("TODO", None)

m["mask_lid"] = str(lid_mask)
m["mask_base"] = str(base_mask)

if depth_npy.exists():
    m["depth_metric_npy"] = str(depth_npy)
    depth_status = "present"
else:
    m["depth_metric_npy"] = "MISSING_DEPTH_RUN_RELABEL_ONLY"
    depth_status = "missing"

m["notes"].append(
    "Updated by gate_d0_fit_v1_update_manifest_manual_assets.py using manual polygon masks and MoGe camera. "
    f"Depth status: {depth_status}."
)

MAN.write_text(json.dumps(m, indent=2))

print("[OK] updated", MAN)
print("[depth_status]", depth_status)
print(json.dumps(m, indent=2))
