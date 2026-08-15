#!/usr/bin/env python
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch
import trimesh

REPO = Path("/home/fredcui/Projects/FollowMyHold")
HAMER_ROOT = REPO / "third_party/estimator/hamer"
if str(HAMER_ROOT) not in sys.path:
    sys.path.insert(0, str(HAMER_ROOT))

from hamer.models import DEFAULT_CHECKPOINT, load_hamer
from hamer.utils.geometry import perspective_projection
from hamer.utils.renderer import Renderer

FINGERTIPS = np.asarray([744, 320, 443, 554, 671], dtype=np.int64)
MANO_TO_OPENPOSE = np.asarray(
    [0, 13, 14, 15, 16, 1, 2, 3, 17, 4, 5, 6, 18, 10, 11, 12, 19, 7, 8, 9, 20],
    dtype=np.int64,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cpu_numpy(value):
    if torch.is_tensor(value):
        return value.detach().cpu().numpy()
    return np.asarray(value)


def json_ready(value):
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if torch.is_tensor(value):
        return value.detach().cpu().tolist()
    if isinstance(value, Path):
        return str(value)
    return value


def immutable_npy(path, array):
    path = Path(path)
    array = np.asarray(array)
    if path.exists():
        old = np.load(path, allow_pickle=False)
        if old.shape != array.shape or not np.array_equal(old, array):
            raise RuntimeError(f"nonidentical_array_exists:{path}")
    else:
        np.save(path, array)
    return {"path": str(path), "sha256": sha(path), "shape": list(array.shape), "dtype": str(array.dtype)}


def load_mesh(path):
    mesh = trimesh.load(Path(path), process=False, maintain_order=True, force="mesh")
    return np.asarray(mesh.vertices, dtype=np.float32), np.asarray(mesh.faces, dtype=np.int64)


def load_matrix(path):
    value = np.load(Path(path), allow_pickle=True)
    if isinstance(value, np.ndarray) and value.shape == (4, 4):
        return value.astype(np.float64)
    if isinstance(value, np.ndarray) and value.shape == ():
        value = value.item()

    def walk(item):
        if isinstance(item, dict):
            for child in item.values():
                found = walk(child)
                if found is not None:
                    return found
        elif isinstance(item, (list, tuple)):
            for child in item:
                found = walk(child)
                if found is not None:
                    return found
        else:
            array = cpu_numpy(item)
            if array.shape == (4, 4):
                return array.astype(np.float64)
        return None

    matrix = walk(value)
    if matrix is None:
        raise RuntimeError(f"no_4x4_matrix:{path}")
    return matrix


def transform_hunyuan_to_moge(vertices, matrix):
    vertices = np.asarray(vertices, dtype=np.float64)
    return (vertices @ matrix[:3, :3].T + matrix[:3, 3]).astype(np.float32)


def metrics(actual, expected):
    actual = np.asarray(actual, dtype=np.float64)
    expected = np.asarray(expected, dtype=np.float64)
    if actual.shape != expected.shape:
        return {"shape_actual": list(actual.shape), "shape_expected": list(expected.shape), "max_abs": None, "rmse": None, "p95_l2": None}
    delta = actual - expected
    flat_l2 = np.linalg.norm(delta.reshape(-1, delta.shape[-1]), axis=1) if delta.ndim >= 2 else np.abs(delta.reshape(-1))
    return {
        "shape_actual": list(actual.shape),
        "shape_expected": list(expected.shape),
        "max_abs": float(np.max(np.abs(delta))) if delta.size else 0.0,
        "rmse": float(np.sqrt(np.mean(delta ** 2))) if delta.size else 0.0,
        "p95_l2": float(np.percentile(flat_l2, 95)) if flat_l2.size else 0.0,
    }


def bound_for(reference, multiplier):
    reference = np.asarray(reference)
    return float(multiplier * np.finfo(np.float32).eps * max(1.0, float(np.max(np.abs(reference)))))


def nested_paths(value):
    found = []
    if isinstance(value, dict):
        for child in value.values():
            found.extend(nested_paths(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(nested_paths(child))
    elif isinstance(value, str) and value.startswith("/"):
        found.append(Path(value))
    return found


def select_array(report_path, include, exclude=()):
    report_path = Path(report_path)
    data = json.loads(report_path.read_text())
    candidates = nested_paths(data)
    candidates.extend(report_path.parent.glob("*.npy"))
    candidates.extend(report_path.parent.glob("**/*.npy"))
    ranked = []
    seen = set()
    for path in candidates:
        path = Path(path)
        if path in seen or not path.is_file() or path.suffix.lower() != ".npy":
            continue
        seen.add(path)
        name = path.name.lower()
        if any(token.lower() in name for token in exclude):
            continue
        score = sum(1 for token in include if token.lower() in name)
        try:
            array = np.asarray(np.load(path, allow_pickle=False)).squeeze()
        except Exception:
            continue
        if array.shape == (21, 2):
            ranked.append((score, str(path), path, array.astype(np.float32)))
    if not ranked:
        raise RuntimeError(f"no_21x2_array_for:{report_path}:include={include}")
    ranked.sort(key=lambda item: (-item[0], item[1]))
    if ranked[0][0] == 0:
        raise RuntimeError(f"no_semantically_named_21x2_array_for:{report_path}:include={include}")
    return ranked[0][2], ranked[0][3]


def flatten_numbers(value, prefix="root"):
    rows = []
    if isinstance(value, dict):
        for key, child in value.items():
            rows.extend(flatten_numbers(child, f"{prefix}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            rows.extend(flatten_numbers(child, f"{prefix}[{index}]"))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        rows.append((prefix.lower(), float(value)))
    return rows


def camera_values(camera_data):
    rows = flatten_numbers(camera_data)

    def choose(required):
        matches = [(key, value) for key, value in rows if all(token in key for token in required)]
        return matches[0][1] if matches else None

    fov = choose(["fov", "x"])
    if fov is None:
        fov = choose(["fov"])
    width = choose(["width"])
    height = choose(["height"])
    if width is None:
        width = choose(["image_size", "1"])
    if height is None:
        height = choose(["image_size", "0"])
    if width is None:
        width = 512.0
    if height is None:
        height = 512.0
    if fov is None:
        raise RuntimeError("camera_fov_not_found")
    return float(fov), int(round(width)), int(round(height))


def mesh_helper_joints(vertices, regressor):
    vertices = np.asarray(vertices, dtype=np.float32)
    regressor = np.asarray(regressor, dtype=np.float32)
    regressed = regressor @ vertices
    fingertips = vertices[FINGERTIPS]
    return np.concatenate([regressed, fingertips], axis=0)[MANO_TO_OPENPOSE].astype(np.float32)


def replay_state(context, model, model_cfg, device):
    inputs = context["inputs"]
    batch_path = Path(inputs["batch"]["path"])
    raw_path = Path(inputs["raw_hand"]["path"])
    h2m_path = Path(inputs["h2m"]["path"])
    candidate = int(context.get("candidate_index", context.get("selected_candidate_index", 0)))
    batch = np.load(batch_path, allow_pickle=True).item()

    params = {}
    for name in ["global_orient", "hand_pose", "betas"]:
        array = cpu_numpy(batch["pred_mano_params"][name])
        params[name] = torch.as_tensor(array[candidate:candidate + 1], dtype=torch.float32, device=device)
    with torch.no_grad():
        output = model.mano(**params, pose2rot=False)
    canonical = output.vertices.detach().cpu().numpy()[0].astype(np.float32, copy=False)

    batch_canonical = cpu_numpy(batch["pred_vertices"])[candidate].astype(np.float32, copy=False)
    canonical_reference = batch_canonical
    replay_record = inputs.get("replay_vertices", {})
    if replay_record and Path(replay_record.get("path", "")).is_file():
        canonical_reference = np.asarray(np.load(replay_record["path"], allow_pickle=False), dtype=np.float32)

    right_flag = float(cpu_numpy(batch["right"])[candidate])
    multiplier = 2.0 * right_flag - 1.0
    handed = canonical.copy()
    handed[:, 0] = multiplier * handed[:, 0]
    camera_translation = cpu_numpy(batch["pred_cam_t_full"])[candidate].astype(np.float32, copy=True)
    renderer = Renderer(model_cfg, faces=model.mano.faces)
    rendered_mesh = renderer.vertices_to_trimesh(handed, camera_translation, (0.65, 0.74, 0.86), is_right=right_flag)
    exported = np.asarray(rendered_mesh.vertices, dtype=np.float32)
    raw_vertices, raw_faces = load_mesh(raw_path)

    pre_h2m_records = inputs.get("pre_h2m_vertex_carriers", [])
    if not isinstance(pre_h2m_records, list):
        raise RuntimeError("pre_h2m_vertex_carriers_must_be_a_list")
    pre_h2m = exported
    pre_h2m_paths = []
    for record in pre_h2m_records:
        carrier_matrix_path = Path(record["path"])
        if record.get("sha256") and sha(carrier_matrix_path) != record["sha256"]:
            raise RuntimeError(f"pre_h2m_carrier_hash_mismatch:{carrier_matrix_path}")
        pre_h2m = transform_hunyuan_to_moge(pre_h2m, load_matrix(carrier_matrix_path))
        pre_h2m_paths.append(carrier_matrix_path)
    matrix = load_matrix(h2m_path)
    shared = transform_hunyuan_to_moge(pre_h2m, matrix)
    if "zero_hand" in inputs:
        shared_path = Path(inputs["zero_hand"]["path"])
    else:
        shared_path = Path(inputs["aligned_hand"]["path"])
    if shared_path.suffix.lower() == ".npy":
        shared_reference = np.asarray(np.load(shared_path, allow_pickle=False), dtype=np.float32).squeeze()
        shared_reference_faces = None
    else:
        shared_reference, shared_reference_faces = load_mesh(shared_path)

    carrier_path = None
    closure = context.get("candidate1_surface_closure", {})
    carrier = closure.get("registered_topology_carrier", {}) if isinstance(closure, dict) else {}
    if isinstance(carrier, dict) and Path(carrier.get("path", "")).is_file():
        carrier_path = Path(carrier["path"])
        registered_faces = np.asarray(np.load(carrier_path, allow_pickle=False), dtype=np.int64)
    else:
        registered_faces = raw_faces.copy()
    if shared_reference_faces is None:
        shared_reference_faces = registered_faces.copy()

    canonical_metric = metrics(canonical, canonical_reference)
    batch_canonical_metric = metrics(canonical, batch_canonical)
    export_metric = metrics(exported, raw_vertices)
    shared_metric = metrics(shared, shared_reference)
    canonical_bound = bound_for(canonical_reference, 16.0)
    export_bound = bound_for(raw_vertices, 128.0)
    shared_bound = bound_for(shared_reference, 256.0)
    checks = {
        "canonical_shape_778x3": canonical.shape == (778, 3),
        "canonical_finite": bool(np.isfinite(canonical).all()),
        "canonical_identity": canonical_metric["max_abs"] is not None and canonical_metric["max_abs"] <= canonical_bound,
        "batch_canonical_identity": batch_canonical_metric["max_abs"] is not None and batch_canonical_metric["max_abs"] <= canonical_bound,
        "handed_export_shape_778x3": exported.shape == (778, 3),
        "handed_export_finite": bool(np.isfinite(exported).all()),
        "handed_export_identity": export_metric["max_abs"] is not None and export_metric["max_abs"] <= export_bound,
        "h2m_shape_4x4": matrix.shape == (4, 4),
        "shared_shape_778x3": shared.shape == (778, 3),
        "shared_finite": bool(np.isfinite(shared).all()),
        "shared_vertex_identity": shared_metric["max_abs"] is not None and shared_metric["max_abs"] <= shared_bound,
        "registered_faces_shape": registered_faces.ndim == 2 and registered_faces.shape[1] == 3,
        "registered_faces_match_shared_reference": registered_faces.shape == shared_reference_faces.shape and bool(np.array_equal(registered_faces, shared_reference_faces)),
    }
    if context.get("decision") in {"pass_v6_candidate1_five_stage_context_with_registered_topology_v45", "pass_v6_candidate1_two_stage_adapter_context_v54"}:
        checks.update({
            "v6_registered_vertex_count_778": shared.shape[0] == 778,
            "v6_registered_face_count_1552": registered_faces.shape == (1552, 3),
            "v6_registered_cap_count_14": registered_faces.shape[0] - 1538 == 14,
        })

    return {
        "candidate": candidate,
        "batch": batch,
        "batch_path": batch_path,
        "raw_path": raw_path,
        "h2m_path": h2m_path,
        "pre_h2m_paths": pre_h2m_paths,
        "shared_path": shared_path,
        "carrier_path": carrier_path,
        "canonical": canonical,
        "exported": exported,
        "pre_h2m": pre_h2m,
        "shared": shared,
        "faces": registered_faces,
        "regressor": cpu_numpy(model.mano.J_regressor).astype(np.float32),
        "right_flag": right_flag,
        "handed_multiplier": multiplier,
        "checks": checks,
        "metrics": {
            "canonical": {**canonical_metric, "bound": canonical_bound},
            "batch_canonical": {**batch_canonical_metric, "bound": canonical_bound},
            "handed_export": {**export_metric, "bound": export_bound},
            "shared_surface": {**shared_metric, "bound": shared_bound},
            "topology": {"vertices": int(shared.shape[0]), "faces": int(registered_faces.shape[0])},
        },
    }


def project_v3(state, context):
    camera_path = Path(context["inputs"]["camera"]["path"])
    camera_data = json.loads(camera_path.read_text())
    fov_x, width, height = camera_values(camera_data)
    try:
        from pytorch3d.renderer import FoVPerspectiveCameras
    except Exception as exc:
        raise RuntimeError(f"pytorch3d_camera_import:{exc}")
    vertices = torch.as_tensor(state["shared"], dtype=torch.float32)
    regressor = torch.as_tensor(state["regressor"], dtype=torch.float32)
    tips = torch.as_tensor(FINGERTIPS, dtype=torch.int64)
    order = torch.as_tensor(MANO_TO_OPENPOSE, dtype=torch.int64)
    joints = torch.cat([regressor @ vertices, vertices.index_select(0, tips)], dim=0).index_select(0, order)
    rotation = torch.tensor([[[-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, -1.0]]], dtype=torch.float32)
    translation = torch.zeros((1, 3), dtype=torch.float32)
    camera = FoVPerspectiveCameras(device="cpu", R=rotation, T=translation, znear=0.01, zfar=100.0, fov=fov_x)
    projected = camera.transform_points_screen(joints.unsqueeze(0), image_size=(height, width))[0, :, :2].detach().cpu().numpy().astype(np.float32)

    h4_path = Path(context["inputs"]["h4_report"]["path"])
    reference_path, reference = select_array(h4_path, include=("project", "keypoint"), exclude=("target",))
    identity = metrics(projected, reference)
    pixel_bound = float(np.finfo(np.float32).eps * 2048.0)

    target = None
    target_path = state["batch_path"].parent / state["batch_path"].name.replace("_cropped_hoi_0.npy", "_kps_for_guidance.npy")
    target_metric = None
    if target_path.is_file():
        payload = np.load(target_path, allow_pickle=True).item()
        target = cpu_numpy(payload["mano_2d_kps"]).squeeze().astype(np.float32)
        target_metric = metrics(projected, target)

    checks = {
        "projection_shape_21x2": projected.shape == (21, 2),
        "projection_finite": bool(np.isfinite(projected).all()),
        "reference_shape_21x2": reference.shape == (21, 2),
        "zero_projection_identity": identity["max_abs"] is not None and identity["max_abs"] <= pixel_bound,
        "camera_fov_finite": bool(np.isfinite(fov_x)),
        "registered_image_size": (height, width) == (512, 512),
    }
    return projected, joints.detach().cpu().numpy().astype(np.float32), checks, {
        "projection_identity": {**identity, "bound": pixel_bound},
        "target_baseline": target_metric,
        "camera": {"fov_x": fov_x, "width": width, "height": height},
        "reference_path": str(reference_path),
        "target_path": str(target_path) if target_path.is_file() else None,
    }, [camera_path, h4_path, reference_path] + ([target_path] if target_path.is_file() else [])


def project_v6(state, context, model_cfg):
    payload_path = Path(context["inputs"]["payload"]["path"])
    raster_path = Path(context["inputs"]["raster"]["path"])
    payload = np.load(payload_path, allow_pickle=True).item()
    target_3d = cpu_numpy(payload["mano_3d_kps"]).squeeze().astype(np.float32)
    target_2d = cpu_numpy(payload["mano_2d_kps"]).squeeze().astype(np.float32)
    target_cam = cpu_numpy(payload["cam_t"]).reshape(-1, 3)[0].astype(np.float32)

    batch = state["batch"]
    candidate = state["candidate"]
    source_3d = cpu_numpy(batch["pred_keypoints_3d"])[candidate].astype(np.float32, copy=True)
    source_3d[:, 0] = state["handed_multiplier"] * source_3d[:, 0]
    source_cam = cpu_numpy(batch["pred_cam_t_full"])[candidate].astype(np.float32, copy=True)

    try:
        from PIL import Image
        with Image.open(raster_path) as image:
            width, height = image.size
    except Exception as exc:
        raise RuntimeError(f"raster_size:{exc}")

    base_focal = float(model_cfg.EXTRA.FOCAL_LENGTH)
    model_size = float(model_cfg.MODEL.IMAGE_SIZE)
    scaled_focal = base_focal / model_size * float(max(height, width))
    points = torch.as_tensor(source_3d[None], dtype=torch.float32)
    translation = torch.as_tensor(source_cam[None], dtype=torch.float32)
    focal = torch.tensor([[scaled_focal, scaled_focal]], dtype=torch.float32)
    center = torch.tensor([[width / 2.0, height / 2.0]], dtype=torch.float32)
    with torch.no_grad():
        projected = perspective_projection(points=points, translation=translation, focal_length=focal, camera_center=center)[0]
    projected = projected.detach().cpu().numpy().astype(np.float32)

    k3_metric = metrics(source_3d, target_3d)
    cam_metric = metrics(source_cam.reshape(1, 3), target_cam.reshape(1, 3))
    projection_metric = metrics(projected, target_2d)
    source_bound = bound_for(target_3d, 32.0)
    cam_bound = bound_for(target_cam, 32.0)
    pixel_bound = float(np.finfo(np.float32).eps * 2048.0)
    checks = {
        "source_3d_shape_21x3": source_3d.shape == (21, 3),
        "source_3d_finite": bool(np.isfinite(source_3d).all()),
        "source_3d_matches_payload": k3_metric["max_abs"] is not None and k3_metric["max_abs"] <= source_bound,
        "camera_shape_3": source_cam.shape == (3,),
        "camera_matches_payload": cam_metric["max_abs"] is not None and cam_metric["max_abs"] <= cam_bound,
        "projection_shape_21x2": projected.shape == (21, 2),
        "projection_finite": bool(np.isfinite(projected).all()),
        "projection_identity": projection_metric["max_abs"] is not None and projection_metric["max_abs"] <= pixel_bound,
        "positive_depth": bool(np.all(source_3d[:, 2] + source_cam[2] > 0.0)),
        "registered_image_size": (height, width) == (512, 512),
    }
    return projected, source_3d, checks, {
        "projection_identity": {**projection_metric, "bound": pixel_bound},
        "source_3d_identity": {**k3_metric, "bound": source_bound},
        "camera_identity": {**cam_metric, "bound": cam_bound},
        "camera": {"scaled_focal": scaled_focal, "width": width, "height": height},
        "target_baseline": projection_metric,
    }, [payload_path, raster_path]


def write_report(path, payload):
    path = Path(path)
    body = json.dumps(json_ready(payload), indent=2, sort_keys=True) + "\n"
    if path.exists():
        if path.read_text() != body:
            print(f"[HOLD] NONIDENTICAL_REPORT_EXISTS={path}")
            return False
        return True
    path.write_text(body)
    return True


def run(context_path, mode, output_dir, report_path):
    context_path = Path(context_path)
    output_dir = Path(output_dir)
    report_path = Path(report_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    errors = []
    context = {}
    try:
        context = json.loads(context_path.read_text())
        decision = context.get("decision")
        if decision in {"pass_v3_adapter_context_bound_v35", "pass_v3_two_stage_adapter_context_v55"}:
            context_id = "v3"
        elif decision in {"pass_v6_candidate1_five_stage_context_with_registered_topology_v45", "pass_v6_candidate1_two_stage_adapter_context_v54"}:
            context_id = "v6_candidate1"
        else:
            raise RuntimeError(f"unsupported_context_decision:{decision}")

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model, model_cfg = load_hamer(DEFAULT_CHECKPOINT)
        model = model.to(device).eval()
        state = replay_state(context, model, model_cfg, device)
        checks = dict(state["checks"])
        numeric = dict(state["metrics"])
        paths = [context_path, state["batch_path"], state["raw_path"], state["h2m_path"], state["shared_path"]]
        paths.extend(state["pre_h2m_paths"])
        if state["carrier_path"] is not None:
            paths.append(state["carrier_path"])

        outputs = {
            "canonical_vertices": immutable_npy(output_dir / "canonical_vertices_v55.npy", state["canonical"]),
            "handed_export_vertices": immutable_npy(output_dir / "handed_export_vertices_v55.npy", state["exported"]),
            "pre_h2m_vertices": immutable_npy(output_dir / "pre_h2m_vertices_v55.npy", state["pre_h2m"]),
            "shared_vertices": immutable_npy(output_dir / "shared_vertices_v55.npy", state["shared"]),
            "registered_faces": immutable_npy(output_dir / "registered_faces_v55.npy", state["faces"]),
        }

        if mode == "zero_surface":
            computed_joints = mesh_helper_joints(state["shared"], state["regressor"])
            outputs["mesh_helper_joints"] = immutable_npy(output_dir / "mesh_helper_joints_v55.npy", computed_joints)
            checks["mesh_helper_joint_shape_21x3"] = computed_joints.shape == (21, 3)
            checks["mesh_helper_joints_finite"] = bool(np.isfinite(computed_joints).all())
            pass_decision = f"pass_{context_id}_zero_surface_identity_v55"
        else:
            if context_id == "v3":
                projected, joints, projection_checks, projection_metrics, projection_paths = project_v3(state, context)
            else:
                projected, joints, projection_checks, projection_metrics, projection_paths = project_v6(state, context, model_cfg)
            checks.update(projection_checks)
            numeric.update(projection_metrics)
            paths.extend(projection_paths)
            outputs["projection_joints"] = immutable_npy(output_dir / "projection_joints_v55.npy", joints)
            outputs["projected_keypoints"] = immutable_npy(output_dir / "projected_keypoints_v55.npy", projected)
            pass_decision = f"pass_{context_id}_zero_projection_identity_v55"

        failed = [name for name, value in checks.items() if not bool(value)]
        final_decision = pass_decision if not failed else f"hold_{context_id}_{mode}_v55"
        unique_paths = []
        seen = set()
        for path in paths:
            path = Path(path)
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            unique_paths.append({"path": str(path), "sha256": sha(path)})
        payload = {
            "schema": "source_bound_zero_adapter_identity_v55",
            "context_id": context_id,
            "mode": mode,
            "decision": final_decision,
            "checks": checks,
            "failed": failed,
            "errors": errors,
            "input_records": unique_paths,
            "adapter_source": {"path": str(Path(__file__)), "sha256": sha(Path(__file__))},
            "newly_computed_outputs": outputs,
            "numeric_metrics": numeric,
            "authorizes_combined_zero_route": not failed,
            "authorizes_nonzero_work": False,
        }
    except Exception as exc:
        context_id = "v3" if "v3" in str(context.get("schema", "")).lower() or context.get("decision") in {"pass_v3_adapter_context_bound_v35", "pass_v3_two_stage_adapter_context_v55"} else "v6_candidate1"
        failed = ["adapter_execution"]
        errors.append(f"{type(exc).__name__}:{exc}")
        payload = {
            "schema": "source_bound_zero_adapter_identity_v55",
            "context_id": context_id,
            "mode": mode,
            "decision": f"hold_{context_id}_{mode}_v55",
            "checks": {},
            "failed": failed,
            "errors": errors,
            "input_records": [{"path": str(context_path), "sha256": sha(context_path)}] if context_path.is_file() else [],
            "adapter_source": {"path": str(Path(__file__)), "sha256": sha(Path(__file__))},
            "newly_computed_outputs": {},
            "numeric_metrics": {},
            "authorizes_combined_zero_route": False,
            "authorizes_nonzero_work": False,
        }
    wrote = write_report(report_path, payload)
    status = "PASS" if payload["decision"].startswith("pass_") and wrote else "HOLD"
    print(f"[{status}] ZERO_ADAPTER_REPORT={report_path} decision={payload['decision']} failed={payload['failed']} errors={payload['errors']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", required=True)
    parser.add_argument("--mode", required=True, choices=["zero_surface", "zero_projection"])
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    run(args.context, args.mode, args.output_dir, args.report)


if __name__ == "__main__":
    main()
