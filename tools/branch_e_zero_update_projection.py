from pathlib import Path
from PIL import Image, ImageDraw
import hashlib
import json
import math
import sys

def write_record(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n")

def main():
    import numpy as np
    import torch
    import trimesh
    from pytorch3d.renderer import FoVPerspectiveCameras

    hand_path = Path(sys.argv[1])
    kps_path = Path(sys.argv[2])
    fov_path = Path(sys.argv[3])
    crop_path = Path(sys.argv[4])
    j_path = Path(sys.argv[5])
    contract_path = Path(sys.argv[6])
    report_path = Path(sys.argv[7])
    projected_path = Path(sys.argv[8])
    panel_path = Path(sys.argv[9])

    contract = json.loads(contract_path.read_text())
    if contract.get("decision") != "pass_source_camera_translation_contract":
        write_record(report_path, {
            "schema": "branch_e_zero_update_projection_v2",
            "decision": "hold_source_contract",
            "failed": ["source_contract"],
            "errors": [],
        })
        print(f"[HOLD] BRANCH_E_ZERO_UPDATE={report_path} reason=source_contract")
        return

    loaded = trimesh.load(hand_path, process=False, force="mesh")
    if isinstance(loaded, trimesh.Scene):
        loaded = loaded.to_geometry()
    vertices_np = np.asarray(loaded.vertices, dtype=np.float32)
    if vertices_np.shape != (778, 3):
        write_record(report_path, {
            "schema": "branch_e_zero_update_projection_v2",
            "decision": "hold_hand_vertex_contract",
            "observed_vertices": list(vertices_np.shape),
            "failed": ["mano_778_vertices"],
            "errors": [],
        })
        print(f"[HOLD] BRANCH_E_ZERO_UPDATE={report_path} reason=mano_778_vertices")
        return

    payload = np.load(kps_path, allow_pickle=True).item()
    target_np = np.asarray(payload["mano_2d_kps"], dtype=np.float32)
    if target_np.shape != (21, 2) or not np.isfinite(target_np).all():
        write_record(report_path, {
            "schema": "branch_e_zero_update_projection_v2",
            "decision": "hold_keypoint_contract",
            "observed_keypoints": list(target_np.shape),
            "failed": ["twenty_one_finite_target_keypoints"],
            "errors": [],
        })
        print(f"[HOLD] BRANCH_E_ZERO_UPDATE={report_path} reason=keypoint_contract")
        return

    with Image.open(crop_path) as image:
        rgb = image.convert("RGB")
        width, height = rgb.size

    fov_x = float(json.loads(fov_path.read_text())["fov_x"])
    vertices = torch.tensor(vertices_np, dtype=torch.float32)
    regressor = torch.load(j_path, map_location="cpu")
    if isinstance(regressor, dict):
        candidates = [value for value in regressor.values()
                      if isinstance(value, torch.Tensor)]
        if len(candidates) == 1:
            regressor = candidates[0]
    regressor = torch.as_tensor(regressor, dtype=torch.float32)

    fingertip_indices = torch.tensor([744, 320, 443, 554, 671])
    mano_to_openpose = torch.tensor(
        [0, 13, 14, 15, 16, 1, 2, 3, 17, 4, 5, 6, 18, 10, 11, 12, 19, 7, 8, 9, 20]
    )

    R = torch.tensor(
        [[[-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, -1.0]]],
        dtype=torch.float32,
    )
    T = torch.zeros((1, 3), dtype=torch.float32)
    camera = FoVPerspectiveCameras(
        device="cpu", R=R, T=T, znear=0.01, zfar=100.0, fov=fov_x
    )

    def project(delta):
        moved = vertices + delta.reshape(1, 3)
        regressed = regressor @ moved
        fingertips = moved.index_select(0, fingertip_indices)
        joints = torch.cat([regressed, fingertips], dim=0)
        joints = joints.index_select(0, mano_to_openpose).unsqueeze(0)
        screen = camera.transform_points_screen(
            joints, image_size=(height, width)
        )[0, :, :2]
        return screen

    zero = torch.zeros(3, dtype=torch.float32, requires_grad=True)
    projected_a = project(zero)
    projected_b = project(torch.zeros(3, dtype=torch.float32))
    jacobian = torch.autograd.functional.jacobian(
        lambda value: project(value).reshape(-1), zero
    )

    projection_np = projected_a.detach().cpu().numpy()
    jacobian_np = jacobian.detach().cpu().numpy()
    singular_values = np.linalg.svd(jacobian_np, compute_uv=False)
    threshold = float(singular_values[0] * 1e-6) if singular_values.size else math.inf
    rank = int(np.sum(singular_values > threshold))

    rmse_px = float(np.sqrt(np.mean((projection_np - target_np) ** 2)))
    max_geometry_delta = float(
        torch.max(torch.abs((vertices + zero.detach()) - vertices)).item()
    )
    deterministic_max_delta = float(
        torch.max(torch.abs(projected_a.detach() - projected_b.detach())).item()
    )
    hand_diag = float(np.linalg.norm(vertices_np.max(axis=0) - vertices_np.min(axis=0)))

    checks = {
        "zero_translation_geometry_identity": max_geometry_delta == 0.0,
        "projection_deterministic": deterministic_max_delta == 0.0,
        "projection_shape_21x2": list(projection_np.shape) == [21, 2],
        "projection_finite": bool(np.isfinite(projection_np).all()),
        "jacobian_shape_42x3": list(jacobian_np.shape) == [42, 3],
        "jacobian_finite": bool(np.isfinite(jacobian_np).all()),
        "translation_locally_rank_three": rank == 3,
        "frozen_hand_diagonal_positive": hand_diag > 0.0,
    }
    failed = [name for name, passed in checks.items() if not passed]

    projected_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(projected_path, projection_np)

    panel = rgb.copy()
    draw = ImageDraw.Draw(panel)
    for x, y in target_np:
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(0, 255, 0))
    for x, y in projection_np:
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 0, 0))
    panel.save(panel_path)

    record = {
        "schema": "branch_e_zero_update_projection_v2",
        "decision": (
            "pass_zero_update_and_observability"
            if not failed else "hold_zero_update_or_observability"
        ),
        "meaning": {
            "green": "frozen_hamer_keypoint_target",
            "red": "c1_v4_hand_at_exactly_zero_delta",
            "rmse_is_acceptance_check": False,
        },
        "camera": contract["camera"],
        "metrics": {
            "baseline_keypoint_rmse_px": rmse_px,
            "zero_geometry_max_abs_delta": max_geometry_delta,
            "deterministic_projection_max_abs_delta": deterministic_max_delta,
            "jacobian_rank": rank,
            "jacobian_singular_values": singular_values.tolist(),
            "frozen_c1_hand_bbox_diagonal": hand_diag,
        },
        "checks": checks,
        "failed": failed,
        "errors": [],
        "outputs": {
            "projected_keypoints": str(projected_path),
            "diagnostic_panel": str(panel_path),
        },
        "authorizations": {
            "write_bounded_solver_contract": not failed,
            "run_nonzero_translation": False,
            "run_c2_v6": False,
            "run_f34": False,
            "run_gate_d": False,
        },
    }
    write_record(report_path, record)
    label = "PASS" if not failed else "HOLD"
    print(
        f"[{label}] BRANCH_E_ZERO_UPDATE={report_path} "
        f"decision={record['decision']} failed={failed}"
    )
    print(f"[INFO] BRANCH_E_ZERO_RMSE_PX={rmse_px}")
    print(f"[INFO] BRANCH_E_TRANSLATION_JACOBIAN_RANK={rank}")
    print(f"[INFO] BRANCH_E_FROZEN_HAND_DIAGONAL={hand_diag}")

try:
    main()
except Exception as exc:
    report = Path(sys.argv[7]) if len(sys.argv) > 7 else Path("branch_e_probe_error.json")
    write_record(report, {
        "schema": "branch_e_zero_update_projection_v2",
        "decision": "hold_probe_runtime_error",
        "failed": ["probe_runtime"],
        "errors": [f"{type(exc).__name__}:{exc}"],
        "authorizations": {
            "run_nonzero_translation": False,
            "run_c2_v6": False,
            "run_f34": False,
            "run_gate_d": False,
        },
    })
    print(f"[HOLD] BRANCH_E_ZERO_UPDATE={report} error={type(exc).__name__}:{exc}")
