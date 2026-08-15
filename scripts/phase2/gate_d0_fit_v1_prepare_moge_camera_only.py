from pathlib import Path
import json
import numpy as np
from PIL import Image

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit_v1_getting_unstuck"
RUN_ROOT = Path("/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_alapuse01_partaware_v2/attempt0_partaware_prompt/run_outputs/arctic_alapuse01_partaware_v2_attempt0")

fov_json = RUN_ROOT / "moge_out/alapuse01_cropped_hoi/fov.json"
image_path = RUN_ROOT / "moge_out/alapuse01_cropped_hoi/image.jpg"
out_meta = FIT / "inputs/alapuse01_moge_camera_from_fov.json"

if not fov_json.exists():
    raise FileNotFoundError(fov_json)
if not image_path.exists():
    raise FileNotFoundError(image_path)

img = Image.open(image_path)
W, H = img.size

fov_data = json.loads(fov_json.read_text())
if isinstance(fov_data, dict):
    for key in ["fov", "fov_x", "fov_deg", "fovy", "fov_y"]:
        if key in fov_data:
            fov = float(fov_data[key])
            break
    else:
        nums = [v for v in fov_data.values() if isinstance(v, (int, float))]
        if not nums:
            raise ValueError(f"Cannot parse numeric fov from {fov_json}: {fov_data}")
        fov = float(nums[0])
else:
    fov = float(fov_data)

fov_rad = np.deg2rad(fov) if fov > 3.2 else fov

fx = fy = 0.5 * W / np.tan(0.5 * fov_rad)
cx = 0.5 * (W - 1)
cy = 0.5 * (H - 1)

meta = {
    "source_fov_json": str(fov_json),
    "source_image": str(image_path),
    "width": int(W),
    "height": int(H),
    "raw_fov_value": fov,
    "fov_rad": float(fov_rad),
    "K": [
        [float(fx), 0.0, float(cx)],
        [0.0, float(fy), float(cy)],
        [0.0, 0.0, 1.0]
    ]
}

out_meta.write_text(json.dumps(meta, indent=2))

print("[OK] wrote", out_meta)
print(json.dumps(meta, indent=2))
