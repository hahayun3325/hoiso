from pathlib import Path
import json

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit_v1_getting_unstuck"
MAN = FIT / "inputs/fit_input_manifest.json"

m = json.loads(MAN.read_text())

cam_meta_path = FIT / "inputs/alapuse01_moge_camera_from_fov.json"
if not cam_meta_path.exists():
    raise FileNotFoundError(cam_meta_path)

cam = json.loads(cam_meta_path.read_text())

lid_mask = FIT / "inputs/alapuse01_lid_mask_coarse_v1.png"
base_mask = FIT / "inputs/alapuse01_base_mask_coarse_v1.png"
depth_npy = FIT / "inputs/alapuse01_moge_metric_depth.npy"

for p in [lid_mask, base_mask, depth_npy]:
    if not p.exists():
        raise FileNotFoundError(p)

m["camera"]["K"] = cam["K"]
m["camera"]["width"] = cam["width"]
m["camera"]["height"] = cam["height"]
m["camera"]["source"] = "moge fov.json converted to pinhole K"
m["camera"].pop("TODO", None)

m["mask_lid"] = str(lid_mask)
m["mask_base"] = str(base_mask)
m["depth_metric_npy"] = str(depth_npy)

m["notes"].append("Updated by gate_d0_fit_v1_update_manifest_from_assets.py using MoGe depth/fov and coarse v1 lid/base masks.")

MAN.write_text(json.dumps(m, indent=2))

print("[OK] updated", MAN)
print(json.dumps(m, indent=2))
