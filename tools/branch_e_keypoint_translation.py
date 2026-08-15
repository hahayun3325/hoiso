from pathlib import Path
from PIL import Image, ImageDraw
import hashlib
import json
import math
import sys

def write_json(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_problem(hand_path, keypoint_path, fov_path, crop_path, regressor_path):
    import numpy as np
    import torch
    import trimesh
    from pytorch3d.renderer import FoVPerspectiveCameras

    mesh = trimesh.load(hand_path, process=False, force="mesh")
    if isinstance(mesh, trimesh.Scene):
        mesh = mesh.to_geometry()
    vertices_np = np.asarray(mesh.vertices, dtype=np.float32)
    faces_np = np.asarray(mesh.faces, dtype=np.int64)
    payload = np.load(keypoint_path, allow_pickle=True).item()
    target_np = np.asarray(payload["mano_2d_kps"], dtype=np.float32)
    with Image.open(crop_path) as image:
        rgb = image.convert("RGB")
        width, height = rgb.size
    fov_x = float(json.loads(fov_path.read_text())["fov_x"])

    regressor = torch.load(regressor_path, map_location="cpu")
    if isinstance(regressor, dict):
        tensors = [value for value in regressor.values()
                   if isinstance(value, torch.Tensor)]
        if len(tensors) == 1:
            regressor = tensors[0]
    regressor = torch.as_tensor(regressor, dtype=torch.float32)
    vertices = torch.tensor(vertices_np, dtype=torch.float32)
    tips = torch.tensor([744, 320, 443, 554, 671], dtype=torch.int64)
    ordering = torch.tensor(
        [0, 13, 14, 15, 16, 1, 2, 3, 17, 4, 5, 6, 18, 10, 11, 12, 19, 7, 8, 9, 20],
        dtype=torch.int64,
    )
    camera = FoVPerspectiveCameras(
        device="cpu",
        R=torch.tensor([[[-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, -1.0]]]),
        T=torch.zeros((1, 3), dtype=torch.float32),
        znear=0.01,
        zfar=100.0,
        fov=fov_x,
    )

    def joints_from_delta(delta):
        moved = vertices + delta.reshape(1, 3)
        return torch.cat(
            [regressor @ moved, moved.index_select(0, tips)], dim=0
        ).index_select(0, ordering).unsqueeze(0)

    def project(delta):
        joints = joints_from_delta(delta)
        return camera.transform_points_screen(
            joints, image_size=(height, width)
        )[0, :, :2]

    return {
        "mesh": mesh,
        "vertices_np": vertices_np,
        "faces_np": faces_np,
        "vertices": vertices,
        "target_np": target_np,
        "target": torch.tensor(target_np, dtype=torch.float32),
        "rgb": rgb,
        "width": width,
        "height": height,
        "camera": camera,
        "joints_from_delta": joints_from_delta,
        "project": project,
    }

def draw_panel(rgb, target, initial, final, output):
    panel = rgb.copy()
    draw = ImageDraw.Draw(panel)
    for x, y in target:
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(0, 255, 0))
    for x, y in initial:
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 0, 0))
    for x, y in final:
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(0, 128, 255))
    output.parent.mkdir(parents=True, exist_ok=True)
    panel.save(output)

def run():
    import numpy as np
    import torch
    import torch.nn.functional as F
    import trimesh

    mode = sys.argv[1]
    hand_path = Path(sys.argv[2])
    keypoint_path = Path(sys.argv[3])
    fov_path = Path(sys.argv[4])
    crop_path = Path(sys.argv[5])
    regressor_path = Path(sys.argv[6])
    policy_path = Path(sys.argv[7])
    baseline_report_path = Path(sys.argv[8])
    baseline_kps_path = Path(sys.argv[9])
    output_path = Path(sys.argv[10])

    policy = json.loads(policy_path.read_text())
    baseline = json.loads(baseline_report_path.read_text())
    problem = load_problem(
        hand_path, keypoint_path, fov_path, crop_path, regressor_path
    )
    zero = torch.zeros(3, dtype=torch.float32)
    initial = problem["project"](zero).detach().cpu().numpy()
    frozen_initial = np.load(baseline_kps_path)
    initial_match = float(np.max(np.abs(initial - frozen_initial)))

    if mode == "no_update":
        checks = {
            "policy_pass": policy.get("decision") == "pass_solver_policy_preregistered",
            "baseline_report_pass": baseline.get("decision") == "pass_zero_update_and_observability",
            "zero_projection_reproduced": initial_match <= 1e-5,
            "zero_geometry_identity": True,
            "no_optimizer_constructed": True,
        }
        failed = [name for name, passed in checks.items() if not passed]
        record = {
            "schema": "branch_e_solver_no_update_identity_v3",
            "decision": "pass_no_update_identity" if not failed else "hold_no_update_identity",
            "checks": checks,
            "failed": failed,
            "errors": [],
            "metrics": {"projection_max_abs_difference": initial_match},
            "inputs": {
                "solver": str(Path(__file__)),
                "solver_sha256": sha(Path(__file__)),
                "policy": str(policy_path),
                "policy_sha256": sha(policy_path),
                "baseline_keypoints": str(baseline_kps_path),
                "baseline_keypoints_sha256": sha(baseline_kps_path),
            },
            "authorizations": {
                "write_launch_contract": not failed,
                "run_solver": False,
                "run_c2_v6": False,
                "run_f34": False,
                "run_gate_d": False,
            },
        }
        write_json(output_path, record)
        label = "PASS" if not failed else "HOLD"
        print(f"[{label}] BRANCH_E_NO_UPDATE={output_path} failed={failed}")
        return

    if mode != "solve":
        write_json(output_path, {
            "schema": "branch_e_translation_trial_v3",
            "decision": "hold_unknown_mode",
            "failed": ["mode"],
            "errors": [],
        })
        print(f"[HOLD] BRANCH_E_SOLVER_MODE={mode}")
        return

    no_update_path = Path(sys.argv[11])
    hand_output = Path(sys.argv[12])
    kps_output = Path(sys.argv[13])
    panel_output = Path(sys.argv[14])
    no_update = json.loads(no_update_path.read_text())
    if no_update.get("decision") != "pass_no_update_identity":
        write_json(output_path, {
            "schema": "branch_e_translation_trial_v3",
            "decision": "hold_no_update_not_passed",
            "failed": ["no_update_identity"],
            "errors": [],
        })
        print(f"[HOLD] BRANCH_E_TRIAL={output_path} reason=no_update_identity")
        return

    if output_path.exists():
        print(f"[HOLD] BRANCH_E_TRIAL_EXISTS={output_path}")
        return

    method = policy["method"]
    trust = policy["trust_region"]
    acceptance = policy["acceptance"]
    radius = float(trust["radius"])
    torch.manual_seed(int(method["seed"]))
    torch.use_deterministic_algorithms(True)

    u = torch.zeros(3, dtype=torch.float32, requires_grad=True)
    optimizer = torch.optim.LBFGS(
        [u],
        lr=float(method["lr"]),
        max_iter=int(method["max_iter"]),
        max_eval=int(method["max_eval"]),
        history_size=int(method["history_size"]),
        line_search_fn=method["line_search_fn"],
        tolerance_grad=float(method["tolerance_grad"]),
        tolerance_change=float(method["tolerance_change"]),
    )
    target = problem["target"]
    losses = []

    def delta_from_u():
        norm = torch.sqrt(torch.sum(u * u) + 1e-12)
        return radius * u / (1.0 + norm)

    def closure():
        optimizer.zero_grad()
        delta = delta_from_u()
        projected = problem["project"](delta)
        keypoint_loss = F.mse_loss(projected, target)
        translation_loss = torch.mean(delta * delta)
        total = 1e-2 * keypoint_loss + 1e-2 * translation_loss
        if torch.isfinite(total):
            total.backward()
        losses.append({
            "total": float(total.detach()),
            "keypoint_mse": float(keypoint_loss.detach()),
            "translation_l2_mean": float(translation_loss.detach()),
        })
        return total

    optimizer.step(closure)
    delta = delta_from_u().detach()
    final = problem["project"](delta).detach().cpu().numpy()
    final_joints = problem["joints_from_delta"](delta)
    final_view = problem["camera"].get_world_to_view_transform().transform_points(
        final_joints
    )[0].detach().cpu().numpy()
    final_view_z = final_view[:, 2]
    target_np = problem["target_np"]
    distances = np.linalg.norm(final - target_np, axis=1)
    initial_distances = np.linalg.norm(initial - target_np, axis=1)
    final_rmse = float(np.sqrt(np.mean((final - target_np) ** 2)))
    initial_rmse = float(np.sqrt(np.mean((initial - target_np) ** 2)))
    palm_width = float(np.linalg.norm(target_np[5] - target_np[17]))
    p95 = float(np.quantile(distances, 0.95))
    trust_fraction = float(torch.linalg.vector_norm(delta).item() / radius)

    translated_vertices = problem["vertices_np"] + delta.cpu().numpy().reshape(1, 3)
    relative_delta = translated_vertices - problem["vertices_np"]
    pure_translation_error = float(
        np.max(np.abs(relative_delta - delta.cpu().numpy().reshape(1, 3)))
    )

    checks = {
        "strict_rmse_improvement": final_rmse < initial_rmse,
        "rmse_over_palm_within_limit":
            palm_width > 0.0 and final_rmse / palm_width <= float(
                acceptance["rmse_over_target_palm_width_max"]
            ),
        "p95_over_palm_within_limit":
            palm_width > 0.0 and p95 / palm_width <= float(
                acceptance["p95_over_target_palm_width_max"]
            ),
        "not_trust_region_saturated":
            trust_fraction < float(trust["maximum_accepted_fraction"]),
        "projected_keypoints_finite": bool(np.isfinite(final).all()),
        "joints_inside_camera_depth_range": bool(
            np.isfinite(final_view_z).all()
            and np.all(final_view_z > 0.01)
            and np.all(final_view_z < 100.0)
        ),
        "projected_keypoints_inside_raster": bool(
            np.all(final[:, 0] >= 0.0)
            and np.all(final[:, 0] < problem["width"])
            and np.all(final[:, 1] >= 0.0)
            and np.all(final[:, 1] < problem["height"])
        ),
        "pure_translation_identity": pure_translation_error <= 1e-7,
        "solver_loss_finite": bool(losses) and all(
            math.isfinite(item["total"]) for item in losses
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]

    hand_output.parent.mkdir(parents=True, exist_ok=True)
    trimesh.Trimesh(
        vertices=translated_vertices,
        faces=problem["faces_np"],
        process=False,
    ).export(hand_output)
    np.save(kps_output, final)
    draw_panel(problem["rgb"], target_np, initial, final, panel_output)

    record = {
        "schema": "branch_e_translation_trial_v3",
        "decision": (
            "pass_branch_e_translation_candidate"
            if not failed else "reject_translation_only_candidate"
        ),
        "one_trial": True,
        "delta_translation_xyz_moge": delta.cpu().numpy().tolist(),
        "metrics": {
            "initial_rmse_px": initial_rmse,
            "final_rmse_px": final_rmse,
            "initial_distance_p95_px": float(np.quantile(initial_distances, 0.95)),
            "final_distance_p95_px": p95,
            "target_palm_width_px": palm_width,
            "final_rmse_over_palm": final_rmse / palm_width if palm_width > 0 else None,
            "final_p95_over_palm": p95 / palm_width if palm_width > 0 else None,
            "trust_radius": radius,
            "trust_fraction": trust_fraction,
            "camera_view_depth_min": float(np.min(final_view_z)),
            "camera_view_depth_max": float(np.max(final_view_z)),
            "pure_translation_max_error": pure_translation_error,
            "closure_evaluations": len(losses),
        },
        "checks": checks,
        "failed": failed,
        "errors": [],
        "loss_history": losses,
        "inputs": {
            "hand": {"path": str(hand_path), "sha256": sha(hand_path)},
            "keypoints": {"path": str(keypoint_path), "sha256": sha(keypoint_path)},
            "policy": {"path": str(policy_path), "sha256": sha(policy_path)},
            "no_update": {"path": str(no_update_path), "sha256": sha(no_update_path)},
            "solver": {"path": str(Path(__file__)), "sha256": sha(Path(__file__))},
        },
        "outputs": {
            "hand": str(hand_output),
            "projected_keypoints": str(kps_output),
            "panel": str(panel_output),
        },
        "authorizations": {
            "run_c2_v6": not failed,
            "run_projection_acceptance": False,
            "run_f34": False,
            "run_gate_d": False,
        },
    }
    write_json(output_path, record)
    label = "PASS" if not failed else "HOLD"
    print(
        f"[{label}] BRANCH_E_TRIAL={output_path} "
        f"decision={record['decision']} failed={failed}"
    )
    print(f"[INFO] BRANCH_E_DELTA_XYZ={record['delta_translation_xyz_moge']}")
    print(f"[INFO] BRANCH_E_FINAL_RMSE_PX={final_rmse}")
    print(f"[INFO] BRANCH_E_FINAL_RMSE_OVER_PALM={record['metrics']['final_rmse_over_palm']}")
    print(f"[INFO] BRANCH_E_FINAL_P95_OVER_PALM={record['metrics']['final_p95_over_palm']}")
    print(f"[INFO] BRANCH_E_TRUST_FRACTION={trust_fraction}")

try:
    run()
except Exception as exc:
    output = Path(sys.argv[10]) if len(sys.argv) > 10 else Path("branch_e_solver_error.json")
    write_json(output, {
        "schema": "branch_e_translation_trial_v3",
        "decision": "hold_solver_runtime_error",
        "failed": ["solver_runtime"],
        "errors": [f"{type(exc).__name__}:{exc}"],
        "authorizations": {
            "run_c2_v6": False,
            "run_f34": False,
            "run_gate_d": False,
        },
    })
    print(f"[HOLD] BRANCH_E_SOLVER={output} error={type(exc).__name__}:{exc}")
