from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shlex
import shutil

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
import trimesh


TIP_IDS = {"index": 320, "middle": 443, "pinky": 671}


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key[7:].strip()
        tokens = shlex.split(raw_value.strip(), comments=True, posix=True)
        values[key] = tokens[0] if tokens else ""
    return values


def as_bool(value: str | None) -> bool:
    return str(value or "0").lower() in {"1", "true", "yes", "on"}


def as_float(value: str | None, default: float) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def load_mesh(path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load(path, force="mesh", process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f"not a triangle mesh: {path}")
    return mesh


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def transformed(vertices: np.ndarray, center: np.ndarray,
                translation: np.ndarray, rotation_deg: np.ndarray) -> np.ndarray:
    matrix = Rotation.from_rotvec(np.deg2rad(rotation_deg)).as_matrix()
    return (vertices - center) @ matrix.T + center + translation


def depth_summary(values: np.ndarray) -> dict[str, float | int]:
    values = np.asarray(values, dtype=np.float64)
    if len(values) == 0:
        return {
            "count": 0,
            "max_m": 0.0,
            "mean_m": 0.0,
            "p95_m": 0.0,
            "count_over_2mm": 0,
            "count_over_5mm": 0,
            "count_over_10mm": 0,
        }
    return {
        "count": int(len(values)),
        "max_m": float(values.max()),
        "mean_m": float(values.mean()),
        "p95_m": float(np.percentile(values, 95)),
        "count_over_2mm": int(np.count_nonzero(values > 0.002)),
        "count_over_5mm": int(np.count_nonzero(values > 0.005)),
        "count_over_10mm": int(np.count_nonzero(values > 0.010)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()

    config_path = Path(args.config)
    cfg = read_env(config_path)
    seed_env_path = Path(cfg.get("GATED_SEED_ENV", ""))
    seed = read_env(seed_env_path)

    hand_path = Path(seed.get("GATED_SEED_HAND", ""))
    object_path = Path(seed.get("GATED_SEED_OBJECT", ""))
    preaudit_path = Path(cfg.get("GATED_PREAUDIT_JSON", ""))
    target_path = Path(cfg.get("GATED_TARGET_CONTRACT", ""))
    side_path = Path(cfg.get("GATED_SIDE_CONTRACT", ""))
    required = {
        "config": config_path,
        "seed_env": seed_env_path,
        "seed_hand": hand_path,
        "seed_object": object_path,
        "preaudit": preaudit_path,
        "target_contract": target_path,
        "side_contract": side_path,
    }
    missing = [f"{name}={path}" for name, path in required.items() if not path.is_file()]
    if missing:
        print(f"[HOLD] GATE_D_BRANCH_INPUT_MISSING={missing}", flush=True)
        return

    safety = {
        "enabled": as_bool(cfg.get("GATED_ENABLE")),
        "hand_root_only": (
            as_bool(cfg.get("GATED_OPT_HAND_ROOT"))
            and not as_bool(cfg.get("GATED_OPT_OBJECT_ROOT"))
            and not as_bool(cfg.get("GATED_OPT_LID_HINGE"))
            and not as_bool(cfg.get("GATED_OPT_HAND_ARTICULATION"))
        ),
        "object_exact": as_bool(cfg.get("GATED_PRESERVE_OBJECT_EXACTLY")),
        "zero_update_selector": as_bool(
            cfg.get("GATED_SELECT_ZERO_UPDATE_IF_NO_SAFE_IMPROVEMENT")
        ),
    }
    print(f"[FOHO_GATE_D_RUNTIME_CONTRACT] config={config_path}", flush=True)
    for name, passed in safety.items():
        print(f"[{'PASS' if passed else 'HOLD'}] GATE_D_SAFETY_{name.upper()}={passed}", flush=True)
    if not all(safety.values()):
        print("[HOLD] GATE_D_BRANCH_SAFETY_CONTRACT_FAILED", flush=True)
        return
    if args.preflight:
        print("[PASS] GATE_D_BRANCH_PREFLIGHT_READY", flush=True)
        return

    hand = load_mesh(hand_path)
    obj = load_mesh(object_path)
    hv0 = np.asarray(hand.vertices, dtype=np.float64)
    ov = np.asarray(obj.vertices, dtype=np.float64)
    if len(hv0) != 778 or max(TIP_IDS.values()) >= len(hv0):
        print(f"[HOLD] GATE_D_HAND_CONTRACT_FAILED vertices={len(hv0)}", flush=True)
        return

    target_data = json.loads(target_path.read_text())
    side_data = json.loads(side_path.read_text())
    target_ids = np.asarray(
        target_data["fixed_object_target_vertex_ids"], dtype=np.int64
    ).reshape(-1)
    target_ids = target_ids[(target_ids >= 0) & (target_ids < len(ov))]
    if len(target_ids) == 0:
        print("[HOLD] GATE_D_TARGET_IDS_INVALID", flush=True)
        return
    target_points = ov[target_ids]
    target_tree = cKDTree(target_points)
    object_tree = cKDTree(ov)
    object_normals = np.asarray(obj.vertex_normals, dtype=np.float64)
    target_center = np.asarray(side_data["target_center"], dtype=np.float64)
    target_normal = np.asarray(side_data["contact_side_normal"], dtype=np.float64)
    target_normal /= max(np.linalg.norm(target_normal), 1e-12)

    max_translation = as_float(cfg.get("GATED_MAX_HAND_TRANS_M"), 0.015)
    max_rotation = as_float(cfg.get("GATED_MAX_HAND_ROT_DEG"), 3.0)
    index_limit = as_float(cfg.get("GATED_INDEX_MAX_DISTANCE_M"), 0.015)
    middle_limit = as_float(cfg.get("GATED_MIDDLE_MAX_DISTANCE_M"), 0.070)
    contact_allowance = as_float(cfg.get("GATED_CONTACT_ALLOWANCE_M"), 0.005)
    clearance = as_float(cfg.get("GATED_NONCONTACT_CLEARANCE_M"), 0.002)

    hand_center = hv0.mean(axis=0)
    hand_diag = float(np.linalg.norm(hand.bounds[1] - hand.bounds[0]))
    contact_radius = max(0.025, 0.035 * hand_diag)
    contact_mask = np.zeros(len(hv0), dtype=bool)
    for tip in (TIP_IDS["index"], TIP_IDS["middle"]):
        contact_mask |= np.linalg.norm(hv0 - hv0[tip], axis=1) <= contact_radius
    near_limit = max(0.080, 0.04 * float(np.linalg.norm(obj.extents)))

    def contact_metrics(hv: np.ndarray) -> dict[str, float]:
        index_d = float(target_tree.query(hv[TIP_IDS["index"]], k=1)[0])
        middle_d = float(target_tree.query(hv[TIP_IDS["middle"]], k=1)[0])
        return {
            "index_distance_m": index_d,
            "middle_distance_m": middle_d,
            "side_index_m": float(
                np.dot(hv[TIP_IDS["index"]] - target_center, target_normal)
            ),
            "side_middle_m": float(
                np.dot(hv[TIP_IDS["middle"]] - target_center, target_normal)
            ),
        }

    def approximate(hv: np.ndarray, translation: np.ndarray,
                    rotation_deg: np.ndarray) -> dict:
        unsigned, nearest = object_tree.query(hv, k=1)
        signed = np.sum((hv - ov[nearest]) * object_normals[nearest], axis=1)
        depth = np.maximum(0.0, -signed)
        near = unsigned <= near_limit
        noncontact = near & ~contact_mask
        approved_contact = near & contact_mask
        contacts = contact_metrics(hv)
        noncontact_depth = depth[noncontact]
        all_near_depth = depth[near]
        contact_excess = np.maximum(
            0.0, depth[approved_contact] - contact_allowance
        )
        nc = depth_summary(noncontact_depth)
        all_depth = depth_summary(all_near_depth)
        barrier = 0.0
        barrier += 200.0 * max(0.0, contacts["index_distance_m"] - index_limit)
        barrier += 100.0 * max(0.0, contacts["middle_distance_m"] - middle_limit)
        barrier += 200.0 * max(0.0, -contacts["side_index_m"])
        barrier += 100.0 * max(0.0, -contacts["side_middle_m"])
        score = (
            2.0 * contacts["index_distance_m"]
            + 0.5 * contacts["middle_distance_m"]
            + 8.0 * float(nc["p95_m"])
            + 4.0 * float(nc["max_m"])
            + 2.0 * float(all_depth["p95_m"])
            + 8.0 * float(contact_excess.mean() if len(contact_excess) else 0.0)
            + 0.10 * float(np.linalg.norm(translation))
            + 0.001 * float(np.linalg.norm(rotation_deg))
            + barrier
        )
        return {
            **contacts,
            "score": float(score),
            "noncontact": nc,
            "all_near_surface": all_depth,
            "translation_m": translation.tolist(),
            "rotation_deg": rotation_deg.tolist(),
        }

    def exact(hv: np.ndarray) -> dict:
        closest, unsigned, face_ids = trimesh.proximity.closest_point(obj, hv)
        normals = np.asarray(obj.face_normals, dtype=np.float64)[face_ids]
        signed = np.sum((hv - closest) * normals, axis=1)
        depth = np.maximum(0.0, -signed)
        near = unsigned <= near_limit
        noncontact = near & ~contact_mask
        approved_contact = near & contact_mask
        contacts = contact_metrics(hv)
        return {
            **contacts,
            "unsigned_min_m": float(unsigned.min()),
            "unsigned_p5_m": float(np.percentile(unsigned, 5)),
            "all_near_surface": depth_summary(depth[near]),
            "noncontact": depth_summary(depth[noncontact]),
            "approved_contact": depth_summary(depth[approved_contact]),
            "depth_per_vertex": depth,
            "unsigned_per_vertex": unsigned,
        }

    zero_state = np.zeros(6, dtype=np.float64)
    current = zero_state.copy()
    current_vertices = hv0.copy()
    current_metrics = approximate(
        current_vertices, current[:3], current[3:]
    )

    schedule = ((0.008, 1.5), (0.004, 0.75), (0.002, 0.375), (0.001, 0.1875))
    evaluations = 1
    for translation_step, rotation_step in schedule:
        for _ in range(2):
            options = [(current.copy(), current_metrics)]
            for axis in range(6):
                step = translation_step if axis < 3 else rotation_step
                for direction in (-1.0, 1.0):
                    proposal = current.copy()
                    proposal[axis] += direction * step
                    if np.linalg.norm(proposal[:3]) > max_translation + 1e-12:
                        continue
                    if np.linalg.norm(proposal[3:]) > max_rotation + 1e-12:
                        continue
                    vertices = transformed(
                        hv0, hand_center, proposal[:3], proposal[3:]
                    )
                    metrics = approximate(vertices, proposal[:3], proposal[3:])
                    options.append((proposal, metrics))
                    evaluations += 1
            proposal, metrics = min(options, key=lambda item: item[1]["score"])
            if metrics["score"] + 1e-12 < current_metrics["score"]:
                current = proposal
                current_metrics = metrics
                current_vertices = transformed(
                    hv0, hand_center, current[:3], current[3:]
                )

    baseline_exact = exact(hv0)
    candidate_exact = exact(current_vertices)
    contact_safe = bool(
        candidate_exact["index_distance_m"] <= index_limit
        and candidate_exact["middle_distance_m"] <= middle_limit
        and candidate_exact["side_index_m"] >= 0.0
        and candidate_exact["side_middle_m"] >= 0.0
        and candidate_exact["approved_contact"]["max_m"]
            <= max(contact_allowance + 0.0025,
                   baseline_exact["approved_contact"]["max_m"])
    )
    nc0 = baseline_exact["noncontact"]
    nc1 = candidate_exact["noncontact"]
    all0 = baseline_exact["all_near_surface"]
    all1 = candidate_exact["all_near_surface"]
    meaningful_improvement = bool(
        nc1["p95_m"] <= nc0["p95_m"] - 0.00025
        or nc1["max_m"] <= nc0["max_m"] - 0.00050
        or nc1["count_over_2mm"] < nc0["count_over_2mm"]
        or all1["max_m"] <= all0["max_m"] - 0.00050
    )
    no_count_regression = bool(
        nc1["count_over_2mm"] <= nc0["count_over_2mm"]
        and all1["count_over_5mm"] <= all0["count_over_5mm"]
    )
    select_update = bool(contact_safe and meaningful_improvement and no_count_regression)

    final_vertices = current_vertices if select_update else hv0
    final_exact = candidate_exact if select_update else baseline_exact
    selection_reason = (
        "bounded root update safely improves penetration"
        if select_update
        else "zero-update retained: no safe strict improvement"
    )

    run_id = cfg.get("GATED_RUN_ID", "gate_d_root_cleanup")
    out_root = Path(cfg.get("GATED_OUT_ROOT", "gate_d_runs"))
    out_root.mkdir(parents=True, exist_ok=True)
    hand_out = out_root / "final_hand_mesh.ply"
    object_out = out_root / "final_obj_mesh.ply"
    metrics_out = out_root / "Gate_D_root_cleanup_metrics.json"
    audit_out = out_root / "Gate_D_root_cleanup_audit.glb"

    final_hand = hand.copy()
    final_hand.vertices = final_vertices
    final_hand.export(hand_out)
    shutil.copy2(object_path, object_out)

    def without_arrays(metrics: dict) -> dict:
        return {
            key: value for key, value in metrics.items()
            if not key.endswith("_per_vertex")
        }

    report = {
        "status": "completed",
        "run_id": run_id,
        "mode": cfg.get("GATED_MODE"),
        "inputs": {
            "hand": str(hand_path),
            "object": str(object_path),
            "target_contract": str(target_path),
            "side_contract": str(side_path),
            "preaudit": str(preaudit_path),
        },
        "outputs": {
            "hand": str(hand_out),
            "object": str(object_out),
            "metrics": str(metrics_out),
            "audit": str(audit_out),
        },
        "search": {
            "evaluations": evaluations,
            "candidate_translation_m": current[:3].tolist(),
            "candidate_translation_norm_m": float(np.linalg.norm(current[:3])),
            "candidate_rotation_deg": current[3:].tolist(),
            "candidate_rotation_norm_deg": float(np.linalg.norm(current[3:])),
            "approximate_candidate": current_metrics,
        },
        "strict_selector": {
            "selected_update": select_update,
            "selection_reason": selection_reason,
            "contact_safe": contact_safe,
            "meaningful_improvement": meaningful_improvement,
            "no_count_regression": no_count_regression,
        },
        "baseline": without_arrays(baseline_exact),
        "candidate": without_arrays(candidate_exact),
        "final": without_arrays(final_exact),
        "object_integrity": {
            "seed_sha256": sha256(object_path),
            "output_sha256": sha256(object_out),
            "byte_identical": sha256(object_path) == sha256(object_out),
            "object_root_optimized": False,
            "lid_hinge_optimized": False,
        },
        "limitations": {
            "open_surface_oriented_depth_is_surrogate": True,
            "visual_audit_required": True,
            "hand_articulation_frozen": True,
        },
    }
    metrics_out.write_text(json.dumps(report, indent=2) + "\n")

    object_view = obj.copy()
    object_view.visual.face_colors = [75, 120, 230, 120]
    hand_view = final_hand.copy()
    hand_view.visual.face_colors = [235, 125, 110, 190]
    scene = trimesh.Scene([object_view, hand_view])
    target_cloud = trimesh.points.PointCloud(
        target_points,
        colors=np.tile([70, 225, 80, 255], (len(target_points), 1)),
    )
    scene.add_geometry(target_cloud, node_name="approved_lid_target")
    final_depth = final_exact["depth_per_vertex"]
    deep_ids = np.flatnonzero(final_depth > clearance)
    if len(deep_ids):
        deep_cloud = trimesh.points.PointCloud(
            final_vertices[deep_ids],
            colors=np.tile([240, 30, 180, 255], (len(deep_ids), 1)),
        )
        scene.add_geometry(deep_cloud, node_name="remaining_suspected_penetration")
    scene.export(audit_out)

    print(f"[FOHO_GATE_D_SEARCH] evaluations={evaluations}", flush=True)
    print(
        "[FOHO_GATE_D_CANDIDATE] "
        f"translation_norm_m={np.linalg.norm(current[:3]):.9f} "
        f"rotation_norm_deg={np.linalg.norm(current[3:]):.6f}",
        flush=True,
    )
    print(
        "[FOHO_GATE_D_BASELINE] "
        f"max_depth_m={all0['max_m']:.9f} "
        f"p95_depth_m={all0['p95_m']:.9f} "
        f"count_over_2mm={all0['count_over_2mm']}",
        flush=True,
    )
    print(
        "[FOHO_GATE_D_FINAL] "
        f"max_depth_m={final_exact['all_near_surface']['max_m']:.9f} "
        f"p95_depth_m={final_exact['all_near_surface']['p95_m']:.9f} "
        f"count_over_2mm={final_exact['all_near_surface']['count_over_2mm']} "
        f"index_m={final_exact['index_distance_m']:.9f} "
        f"middle_m={final_exact['middle_distance_m']:.9f}",
        flush=True,
    )
    if select_update:
        print("[PASS] GATE_D_BOUNDED_ROOT_UPDATE_SELECTED", flush=True)
    else:
        print("[HOLD] GATE_D_ZERO_UPDATE_RETAINED", flush=True)
    print(f"[PASS] GATE_D_FINAL_HAND={hand_out}", flush=True)
    print(f"[PASS] GATE_D_FINAL_OBJECT={object_out}", flush=True)
    print(f"[PASS] GATE_D_METRICS_WRITTEN={metrics_out}", flush=True)
    print(f"[PASS] GATE_D_AUDIT_WRITTEN={audit_out}", flush=True)
    print("[FOHO_GATE_D_FINAL_AUDIT_READY]", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"[HOLD] GATE_D_ROOT_CLEANUP_FAILED={type(error).__name__}: {error}", flush=True)
