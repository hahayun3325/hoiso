from pathlib import Path
import json
import numpy as np
from PIL import Image

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit_v1_getting_unstuck"
RUN_ROOT = Path("/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_alapuse01_partaware_v2/attempt0_partaware_prompt/run_outputs/arctic_alapuse01_partaware_v2_attempt0")

depth_exr = RUN_ROOT / "moge_out/alapuse01_cropped_hoi/depth.exr"
fov_json = RUN_ROOT / "moge_out/alapuse01_cropped_hoi/fov.json"
image_path = RUN_ROOT / "moge_out/alapuse01_cropped_hoi/image.jpg"

out_depth = FIT / "inputs/alapuse01_moge_metric_depth.npy"
out_meta = FIT / "inputs/alapuse01_moge_camera_from_fov.json"

if not depth_exr.exists():
    raise FileNotFoundError(depth_exr)
if not fov_json.exists():
    raise FileNotFoundError(fov_json)
if not image_path.exists():
    raise FileNotFoundError(image_path)

# Try OpenCV first. If EXR support is disabled, the script will tell you.
try:
    import cv2
    depth = cv2.imread(str(depth_exr), cv2.IMREAD_UNCHANGED)
    if depth is None:
        raise RuntimeError("cv2.imread returned None")
    if depth.ndim == 3:
        depth = depth[..., 0]
    depth = depth.astype(np.float32)
except Exception as e:
    raise RuntimeError(
        "Could not read depth.exr with OpenCV. Install/enable EXR support or export depth from MoGe as .npy. "
        f"Original error: {e}"
    )

# Read image size.
img = Image.open(image_path)
W, H = img.size

# Read fov. Handle common formats.
fov_data = json.loads(fov_json.read_text())
if isinstance(fov_data, dict):
    if "fov" in fov_data:
        fov = float(fov_data["fov"])
    elif "fov_x" in fov_data:
        fov = float(fov_data["fov_x"])
    elif "fov_deg" in fov_data:
        fov = float(fov_data["fov_deg"])
    else:
        vals = [v for v in fov_data.values() if isinstance(v, (int, float))]
        if not vals:
            raise ValueError(f"Cannot find numeric fov in {fov_json}: {fov_data}")
        fov = float(vals[0])
else:
    fov = float(fov_data)

# Convert degrees to radians if needed.
if fov > 3.2:
    fov_rad = np.deg2rad(fov)
else:
    fov_rad = fov

fx = fy = 0.5 * W / np.tan(0.5 * fov_rad)
cx = 0.5 * (W - 1)
cy = 0.5 * (H - 1)

K = [
    [float(fx), 0.0, float(cx)],
    [0.0, float(fy), float(cy)],
    [0.0, 0.0, 1.0]
]

np.save(out_depth, depth)

meta = {
    "source_depth_exr": str(depth_exr),
    "source_fov_json": str(fov_json),
    "source_image": str(image_path),
    "width": int(W),
    "height": int(H),
    "raw_fov_value": fov,
    "fov_rad": float(fov_rad),
    "K": K,
    "depth_npy": str(out_depth),
    "depth_stats": {
        "shape": list(depth.shape),
        "finite_ratio": float(np.isfinite(depth).mean()),
        "min": float(np.nanmin(depth)),
        "max": float(np.nanmax(depth)),
        "mean": float(np.nanmean(depth))
    }
}

out_meta.write_text(json.dumps(meta, indent=2))

print("[OK] wrote", out_depth)
print("[OK] wrote", out_meta)
print(json.dumps(meta, indent=2))
