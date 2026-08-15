#!/usr/bin/env python3
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import torch


EXPECTED_ALPHAS = np.asarray([-0.50, -0.25, 0.00, 0.25, 0.50, 0.75, 1.00], dtype=np.float64)
EXECUTION_ORDER = [-0.25, 0.25, -0.50, 0.50, 0.75, 1.00]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def require_file(path, expected_sha256=None):
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"missing_input:{path}")
    digest = sha(path)
    if expected_sha256 is not None and digest != expected_sha256:
        raise RuntimeError(f"hash_mismatch:{path}:expected={expected_sha256}:actual={digest}")
    return path, digest


def write_array_immutable(path, array):
    path = Path(path)
    array = np.asarray(array)
    if path.exists():
        previous = np.load(path, allow_pickle=False)
        if previous.shape != array.shape or not np.array_equal(previous, array):
            raise RuntimeError(f"nonidentical_array_exists:{path}")
    else:
        np.save(path, array, allow_pickle=False)


def write_text_immutable(path, text):
    path = Path(path)
    if path.exists() and path.read_text() != text:
        raise RuntimeError(f"nonidentical_text_exists:{path}")
    if not path.exists():
        path.write_text(text)


def load_candidate(path, expected_sha256):
    path, digest = require_file(path, expected_sha256)
    spec = importlib.util.spec_from_file_location("candidate5_v75_frozen", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    required = ["load_hamer", "replay_state", "project_v3"]
    missing = [name for name in required if not callable(getattr(module, name, None))]
    if missing:
        raise RuntimeError(f"candidate_api_missing:{missing}")
    return module, digest


def load_one_model(candidate, checkpoint, device):
    resolved = checkpoint
    if resolved is None:
        resolved = getattr(candidate, "DEFAULT_CHECKPOINT", None)
    if resolved is None:
        raise RuntimeError("checkpoint_not_resolved")
    resolved = Path(resolved)
    require_file(resolved)
    model, model_cfg = candidate.load_hamer(str(resolved))
    model = model.to(device)
    model.eval()
    return model, model_cfg, resolved


def sync_and_release(device, state=None):
    if state is not None:
        del state
    if device.type == "cuda":
        torch.cuda.synchronize(device)
        torch.cuda.empty_cache()


def array_metrics(actual, expected):
    actual = np.asarray(actual, dtype=np.float64)
    expected = np.asarray(expected, dtype=np.float64)
    delta = actual - expected
    return {
        "max_abs": float(np.max(np.abs(delta))),
        "rmse": float(np.sqrt(np.mean(delta * delta))),
        "l2": float(np.linalg.norm(delta)),
    }


def structural_state_checks(state):
    checks = state.get("checks", {})
    required = [
        "canonical_shape_778x3", "canonical_finite", "handed_export_shape_778x3",
        "handed_export_finite", "h2m_shape_4x4", "shared_shape_778x3",
        "shared_finite", "registered_faces_shape", "registered_faces_match_shared_reference",
    ]
    return {name: bool(checks.get(name)) for name in required}


def project_sample(candidate, context, model, model_cfg, device, parameter_map, direction, alpha):
    physical = np.asarray(alpha * direction, dtype=np.float64)
    order = list(parameter_map["parameter_order"])
    if len(order) != 18 or physical.shape != (21,):
        raise RuntimeError(f"unexpected_parameter_shape:order={len(order)}:physical={physical.shape}")
    articulation = {} if alpha == 0.0 else {name: float(value) for name, value in zip(order, physical[3:])}
    translation = np.zeros(3, dtype=np.float32) if alpha == 0.0 else physical[:3].astype(np.float32)
    state = candidate.replay_state(
        context, model, model_cfg, device,
        deltas=articulation,
        parameter_map=parameter_map,
    )
    projected, joints, projection_checks, projection_meta, _ = candidate.project_v3(
        state, context, hand_translation_moge=translation,
    )
    projected = np.asarray(projected, dtype=np.float32)
    joints = np.asarray(joints, dtype=np.float32)
    structural = structural_state_checks(state)
    checks = {
        "projected_shape_21x2": projected.shape == (21, 2),
        "joints_shape_21x3": joints.shape == (21, 3),
        "projected_finite": bool(np.isfinite(projected).all()),
        "joints_finite": bool(np.isfinite(joints).all()),
        "structural_state_checks": bool(structural) and all(structural.values()),
        "projection_shape_check": bool(projection_checks.get("projection_shape_21x2")),
        "projection_finite_check": bool(projection_checks.get("projection_finite")),
    }
    record = {
        "alpha": float(alpha),
        "translation": translation.astype(np.float64).tolist(),
        "maximum_absolute_articulation_delta": float(np.max(np.abs(physical[3:]))),
        "checks": checks,
        "structural_state_checks": structural,
        "projection_identity_check_is_expected_only_at_zero": bool(projection_checks.get("zero_projection_identity")),
        "camera": projection_meta.get("camera"),
    }
    return projected, joints, record, state


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-source", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--parameter-map", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--direction", required=True)
    parser.add_argument("--normalized-direction", required=True)
    parser.add_argument("--alphas", required=True)
    parser.add_argument("--linear-predictions", required=True)
    parser.add_argument("--zero-reference", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--checkpoint")
    parser.add_argument("--device", default="cuda:0")
    return parser.parse_args()


def main():
    args = parse_args()
    policy_path, policy_sha = require_file(args.policy)
    policy = read_json(policy_path)
    if policy.get("decision") != "pass_v90_bound_vs_curvature_probe_policy_preregistered":
        raise RuntimeError(f"policy_not_passed:{policy.get('decision')}")

    candidate_record = policy.get("source", {})
    candidate, candidate_sha = load_candidate(args.candidate_source, args.candidate_sha256)
    if candidate_record.get("selected_sha256") != candidate_sha:
        raise RuntimeError("candidate_policy_hash_mismatch")

    context_path, context_sha = require_file(args.context)
    parameter_map_path, parameter_map_sha = require_file(args.parameter_map)
    direction_path, direction_sha = require_file(args.direction, policy["outputs"]["physical_direction"]["sha256"])
    normalized_path, normalized_sha = require_file(args.normalized_direction, policy["outputs"]["normalized_direction"]["sha256"])
    alphas_path, alphas_sha = require_file(args.alphas, policy["outputs"]["alphas"]["sha256"])
    linear_path, linear_sha = require_file(args.linear_predictions, policy["outputs"]["linear_predictions"]["sha256"])
    zero_path, zero_sha = require_file(args.zero_reference)
    target_path, target_sha = require_file(args.target)

    context = read_json(context_path)
    parameter_map = read_json(parameter_map_path)
    direction = np.asarray(np.load(direction_path, allow_pickle=False), dtype=np.float64)
    normalized_direction = np.asarray(np.load(normalized_path, allow_pickle=False), dtype=np.float64)
    alphas = np.asarray(np.load(alphas_path, allow_pickle=False), dtype=np.float64)
    linear = np.asarray(np.load(linear_path, allow_pickle=False), dtype=np.float64)
    zero_reference = np.asarray(np.load(zero_path, allow_pickle=False), dtype=np.float64).squeeze()
    target = np.asarray(np.load(target_path, allow_pickle=False), dtype=np.float64).squeeze()

    if direction.shape != normalized_direction.shape or direction.shape != (21,):
        raise RuntimeError(f"direction_shape_mismatch:{direction.shape}:{normalized_direction.shape}")
    if not np.array_equal(alphas, EXPECTED_ALPHAS):
        raise RuntimeError(f"alpha_schedule_mismatch:{alphas.tolist()}")
    if linear.shape != (7, 21, 2) or zero_reference.shape != (21, 2) or target.shape != (21, 2):
        raise RuntimeError(f"projection_shape_mismatch:{linear.shape}:{zero_reference.shape}:{target.shape}")
    if np.linalg.norm(normalized_direction[:3]) > 1.0 + 1e-6 or np.max(np.abs(normalized_direction[3:])) > 1.0 + 1e-6:
        raise RuntimeError("direction_exceeds_registered_bounds")
    if not all(np.isfinite(array).all() for array in [direction, normalized_direction, alphas, linear, zero_reference, target]):
        raise RuntimeError("nonfinite_frozen_array")

    device = torch.device(args.device)
    model, model_cfg, checkpoint_path = load_one_model(candidate, args.checkpoint, device)
    output_dir = Path(args.out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    projections = np.empty((7, 21, 2), dtype=np.float32)
    joints = np.empty((7, 21, 3), dtype=np.float32)
    restorations = np.empty((6, 21, 2), dtype=np.float32)
    sample_records = []
    restoration_records = []
    alpha_to_index = {float(value): index for index, value in enumerate(alphas)}

    initial_zero, initial_joints, initial_record, state = project_sample(
        candidate, context, model, model_cfg, device, parameter_map, direction, 0.0,
    )
    sync_and_release(device, state)
    zero_index = alpha_to_index[0.0]
    projections[zero_index] = initial_zero
    joints[zero_index] = initial_joints
    initial_record["zero_reference_metrics"] = array_metrics(initial_zero, zero_reference)
    sample_records.append(initial_record)

    zero_bound = float(policy["thresholds"]["zero_restoration_max_abs_px"])
    if initial_record["zero_reference_metrics"]["max_abs"] > zero_bound:
        raise RuntimeError(f"initial_zero_identity_failed:{initial_record['zero_reference_metrics']}")

    for restoration_index, alpha in enumerate(EXECUTION_ORDER):
        if alpha not in alpha_to_index:
            raise RuntimeError(f"execution_alpha_not_registered:{alpha}")
        if abs(alpha) * np.linalg.norm(normalized_direction[:3]) > 1.0 + 1e-6:
            raise RuntimeError(f"translation_bound_exceeded:{alpha}")
        if abs(alpha) * np.max(np.abs(normalized_direction[3:])) > 1.0 + 1e-6:
            raise RuntimeError(f"articulation_bound_exceeded:{alpha}")

        projected, sample_joints, record, state = project_sample(
            candidate, context, model, model_cfg, device, parameter_map, direction, alpha,
        )
        sync_and_release(device, state)
        index = alpha_to_index[float(alpha)]
        projections[index] = projected
        joints[index] = sample_joints
        record["linear_reference_metrics"] = array_metrics(projected, linear[index])
        record["target_residual_l2"] = float(np.linalg.norm(target - projected))
        sample_records.append(record)

        restored, _, restore_record, state = project_sample(
            candidate, context, model, model_cfg, device, parameter_map, direction, 0.0,
        )
        sync_and_release(device, state)
        restorations[restoration_index] = restored
        restore_record["after_alpha"] = float(alpha)
        restore_record["initial_zero_metrics"] = array_metrics(restored, initial_zero)
        restoration_records.append(restore_record)
        if restore_record["initial_zero_metrics"]["max_abs"] > zero_bound:
            raise RuntimeError(f"zero_restoration_failed:alpha={alpha}:metrics={restore_record['initial_zero_metrics']}")

    structural_pass = all(all(item["checks"].values()) for item in sample_records + restoration_records)
    repeatability_max = float(max(item["initial_zero_metrics"]["max_abs"] for item in restoration_records))
    runtime_checks = {
        "all_sample_structural_checks_pass": structural_pass,
        "initial_zero_identity_pass": initial_record["zero_reference_metrics"]["max_abs"] <= zero_bound,
        "all_zero_restorations_pass": repeatability_max <= float(policy["thresholds"]["repeatability_max_abs_px"]),
        "projection_shape_exact": projections.shape == (7, 21, 2),
        "restoration_shape_exact": restorations.shape == (6, 21, 2),
        "all_outputs_finite": bool(all(np.isfinite(array).all() for array in [projections, joints, restorations])),
    }
    failed = [name for name, value in runtime_checks.items() if not bool(value)]
    decision = "pass_v91_raw_curvature_probe_collection" if not failed else "hold_v91_raw_curvature_probe_collection"

    projection_out = output_dir / "nonlinear_projections_v91.npy"
    joint_out = output_dir / "nonlinear_joints_v91.npy"
    restoration_out = output_dir / "zero_restoration_projections_v91.npy"
    write_array_immutable(projection_out, projections)
    write_array_immutable(joint_out, joints)
    write_array_immutable(restoration_out, restorations)

    report = {
        "schema": "v91_raw_bound_vs_curvature_probe_collection",
        "decision": decision,
        "checks": runtime_checks,
        "failed": failed,
        "errors": [],
        "alpha_schedule": alphas.tolist(),
        "execution_order": EXECUTION_ORDER,
        "sample_records": sample_records,
        "restoration_records": restoration_records,
        "repeatability_max_abs_px": repeatability_max,
        "inputs": {
            "policy": {"path": str(policy_path), "sha256": policy_sha},
            "candidate": {"path": str(args.candidate_source), "sha256": candidate_sha},
            "context": {"path": str(context_path), "sha256": context_sha},
            "parameter_map": {"path": str(parameter_map_path), "sha256": parameter_map_sha},
            "direction": {"path": str(direction_path), "sha256": direction_sha},
            "normalized_direction": {"path": str(normalized_path), "sha256": normalized_sha},
            "alphas": {"path": str(alphas_path), "sha256": alphas_sha},
            "linear_predictions": {"path": str(linear_path), "sha256": linear_sha},
            "zero_reference": {"path": str(zero_path), "sha256": zero_sha},
            "target": {"path": str(target_path), "sha256": target_sha},
            "checkpoint": {"path": str(checkpoint_path), "sha256": sha(checkpoint_path)},
        },
        "outputs": {
            "projections": {"path": str(projection_out), "sha256": sha(projection_out)},
            "joints": {"path": str(joint_out), "sha256": sha(joint_out)},
            "restorations": {"path": str(restoration_out), "sha256": sha(restoration_out)},
        },
        "authorizes_scientific_analysis": not failed,
        "authorizes_optimizer": False,
    }
    report_path = output_dir / "raw_curvature_probe_report_v91.json"
    write_text_immutable(report_path, json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"[{'PASS' if not failed else 'HOLD'}] V91_RAW_REPORT={report_path} decision={decision} failed={failed} errors=[]")


if __name__ == "__main__":
    main()
