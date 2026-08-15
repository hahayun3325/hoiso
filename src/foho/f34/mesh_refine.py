from pathlib import Path
import itertools
import json
import os
import sys

IMPORT_ERROR = None
try:
    import numpy as np
    import trimesh
    from scipy.spatial import cKDTree
except Exception as exc:
    IMPORT_ERROR = exc


def get_arg(argv, name, default=""):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
    return default


def parse_env(path):
    data = {}
    p = Path(path)
    if not p.is_file():
        print(f"[HOLD] F3_4_CONFIG_MISSING={p}")
        return data

    for raw in p.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        data[key.strip()] = val.strip().strip('"').strip("'")
    return data


def as_bool(v):
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


def as_float(v, default):
    try:
        return float(v)
    except Exception:
        return default


def load_mesh(path):
    p = Path(path)
    if not p.is_file():
        print(f"[HOLD] F3_4_MESH_MISSING={p}")
        return None

    try:
        m = trimesh.load_mesh(p, process=False)
        if isinstance(m, trimesh.Scene):
            if not m.geometry:
                print(f"[HOLD] F3_4_EMPTY_SCENE={p}")
                return None
            m = trimesh.util.concatenate(tuple(m.geometry.values()))
        if not isinstance(m, trimesh.Trimesh):
            print(f"[HOLD] F3_4_NOT_TRIMESH={p}")
            return None
        return m
    except Exception as exc:
        print(f"[HOLD] F3_4_MESH_LOAD_FAILED={type(exc).__name__}: {exc}")
        return None


def make_mesh_like(mesh, vertices):
    return trimesh.Trimesh(
        vertices=np.asarray(vertices, dtype=np.float64),
        faces=np.asarray(mesh.faces),
        process=False,
    )


def contains_count(hand_mesh, obj_vertices):
    try:
        if not hand_mesh.is_watertight:
            return None
        return int(np.asarray(hand_mesh.contains(np.asarray(obj_vertices)), dtype=bool).sum())
    except Exception as exc:
        print(f"[INFO] F3_4_CONTAINMENT_SKIPPED={type(exc).__name__}: {exc}")
        return None


def color_mesh(mesh, rgba):
    m = mesh.copy()
    m.visual.vertex_colors = np.tile(np.asarray(rgba, dtype=np.uint8), (len(m.vertices), 1))
    return m


def marker(point, radius, rgba):
    s = trimesh.creation.icosphere(subdivisions=2, radius=radius)
    s.apply_translation(point)
    s.visual.vertex_colors = np.tile(np.asarray(rgba, dtype=np.uint8), (len(s.vertices), 1))
    return s


def main(argv):
    if IMPORT_ERROR is not None:
        print(f"[HOLD] F3_4_IMPORT_FAILED={type(IMPORT_ERROR).__name__}: {IMPORT_ERROR}")
        return

    cfg_path = get_arg(argv, "--config")
    preflight = "--preflight" in argv

    if not cfg_path:
        print("[HOLD] F3_4_CONFIG_ARG_MISSING")
        return

    cfg = parse_env(cfg_path)
    if not cfg:
        return

    enabled = as_bool(os.environ.get("FOHO_F3_4_ENABLE", cfg.get("FOHO_F3_4_ENABLE", "0")))
    if not enabled:
        print("[HOLD] F3_4_NOT_ENABLED")
        return

    target_contract_path = os.environ.get(
        "FOHO_F3_4_TARGET_CONTRACT_JSON",
        cfg.get("FOHO_F3_4_TARGET_CONTRACT_JSON", ""),
    )

    print(
        "[FOHO_F3_4_RUNTIME_CONTRACT] "
        f"mode={cfg.get('FOHO_F3_4_MODE', 'safe_root_pre_gateD')} "
        f"config={cfg_path}"
    )

    if not Path(target_contract_path).is_file():
        print(f"[HOLD] F3_4_TARGET_CONTRACT_MISSING={target_contract_path}")
        return

    try:
        contract = json.loads(Path(target_contract_path).read_text())
    except Exception as exc:
        print(f"[HOLD] F3_4_TARGET_CONTRACT_READ_FAILED={type(exc).__name__}: {exc}")
        return

    print(f"[FOHO_F3_4_TARGET_FRAME_CONTRACT] json={target_contract_path}")

    selector_state = os.environ.get(
        "FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR",
        cfg.get("FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR", "0"),
    )

    opt_object_root = as_bool(cfg.get("FOHO_F3_4_OPT_OBJECT_ROOT", "1"))
    opt_lid_hinge = str(cfg.get("FOHO_F3_4_OPT_LID_HINGE", "0")).lower()

    max_hand_t = as_float(cfg.get("FOHO_F3_4_MAX_HAND_TRANS_M", "0.060"), 0.060)
    max_obj_t = as_float(cfg.get("FOHO_F3_4_MAX_OBJECT_TRANS_M", "0.020"), 0.020)
    max_hand_rot = as_float(cfg.get("FOHO_F3_4_MAX_HAND_ROT_DEG", "0.0"), 0.0)
    max_obj_rot = as_float(cfg.get("FOHO_F3_4_MAX_OBJECT_ROT_DEG", "0.0"), 0.0)

    print(
        "[FOHO_F3_4_BOUNDED_DOF_CONTRACT] "
        f"hand_trans_m={max_hand_t} object_trans_m={max_obj_t} "
        f"hand_rot_deg={max_hand_rot} object_rot_deg={max_obj_rot} "
        f"object_root={int(opt_object_root)} lid_hinge={opt_lid_hinge}"
    )

    print(f"[FOHO_F3_4_SELECTOR_DISABLED] FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR={selector_state}")

    if selector_state != "0":
        print("[HOLD] F3_4_SELECTOR_NOT_DISABLED")
        return

    if opt_lid_hinge not in {"0", "false", "off", "none"}:
        hinge_json = cfg.get("FOHO_F3_4_HINGE_METADATA_JSON", "")
        if not Path(hinge_json).is_file():
            print("[HOLD] F3_4_HINGE_REQUESTED_BUT_METADATA_MISSING")
            print("[FOHO_F3_4_HINGE_POLICY] disabled_for_safety")
            return
        print(f"[FOHO_F3_4_HINGE_POLICY] metadata={hinge_json}")
    else:
        print("[FOHO_F3_4_HINGE_POLICY] disabled_first_trial_preserve_gate_a_object")

    if max_hand_rot != 0.0 or max_obj_rot != 0.0:
        print("[HOLD] F3_4_SAFE_ROOT_BRANCH_IS_TRANSLATION_ONLY_SET_ROTATION_BOUNDS_TO_ZERO")
        return

    if preflight:
        print("[PASS] F3_4_PREFLIGHT_READY")
        return

    hand_path = cfg.get("FOHO_F3_4_INIT_HAND_PLY") or contract.get("hand_path", "")
    obj_path = cfg.get("FOHO_F3_4_INIT_OBJECT_PLY") or contract.get("final_object_path", "")

    hand = load_mesh(hand_path)
    obj = load_mesh(obj_path)
    if hand is None or obj is None:
        return

    target_ids = np.asarray(contract.get("fixed_object_target_vertex_ids", []), dtype=np.int64)

    if target_ids.size == 0:
        print("[HOLD] F3_4_TARGET_IDS_MISSING_IN_CONTRACT")
        return
    if target_ids.min() < 0 or target_ids.max() >= len(obj.vertices):
        print("[HOLD] F3_4_TARGET_IDS_NOT_VALID_FOR_OBJECT")
        return

    tip_ids = {"index": 320, "middle": 443, "pinky": 671}
    if max(tip_ids.values()) >= len(hand.vertices):
        print("[HOLD] F3_4_MANO_TIP_IDS_INVALID_FOR_HAND")
        return

    hv0 = np.asarray(hand.vertices, dtype=np.float64)
    ov0 = np.asarray(obj.vertices, dtype=np.float64)

    def eval_fast(hand_t, obj_t):
        hv = hv0 + np.asarray(hand_t)
        ov = ov0 + np.asarray(obj_t)

        target_points = ov[target_ids]
        target_tree = cKDTree(target_points)

        index_d = float(target_tree.query(hv[tip_ids["index"]], k=1)[0])
        middle_d = float(target_tree.query(hv[tip_ids["middle"]], k=1)[0])
        mean_contact = 0.5 * (index_d + middle_d)

        obj_tree = cKDTree(ov)
        hand_to_obj = obj_tree.query(hv, k=1)[0]
        p5 = float(np.percentile(hand_to_obj, 5))

        proximity_penalty = abs(p5 - 0.006)

        transform_penalty = (
            0.04 * float(np.linalg.norm(hand_t))
            + 0.20 * float(np.linalg.norm(obj_t))
        )

        score = mean_contact + proximity_penalty + transform_penalty
        return score, index_d, middle_d, p5

    def vals(maxv, n):
        if maxv <= 0:
            return [0.0]
        if n == 3:
            return [-maxv, 0.0, maxv]
        return [-maxv, -0.5 * maxv, 0.0, 0.5 * maxv, maxv]

    hand_vals = vals(max_hand_t, 5)
    obj_vals = vals(max_obj_t, 3) if opt_object_root else [0.0]

    coarse = []
    for ht in itertools.product(hand_vals, hand_vals, hand_vals):
        for ot in itertools.product(obj_vals, obj_vals, obj_vals):
            score, index_d, middle_d, p5 = eval_fast(ht, ot)
            coarse.append({
                "hand_translation_m": [float(x) for x in ht],
                "object_translation_m": [float(x) for x in ot],
                "fast_score": float(score),
                "index_distance_m": float(index_d),
                "middle_distance_m": float(middle_d),
                "p5_hand_to_object_m": float(p5),
            })

    coarse.sort(key=lambda x: x["fast_score"])

    print(
        "[FOHO_F3_4_STAGE_A_CONTACT_PROXIMITY] "
        f"candidates={len(coarse)} "
        f"best_index={coarse[0]['index_distance_m']:.6f} "
        f"best_middle={coarse[0]['middle_distance_m']:.6f}"
    )

    refined = []
    for c in coarse[:60]:
        hv = hv0 + np.asarray(c["hand_translation_m"])
        ov = ov0 + np.asarray(c["object_translation_m"])

        hm = make_mesh_like(hand, hv)
        inside = contains_count(hm, ov)

        inside_penalty = 0.0 if inside is None else max(0, inside - 617) * 0.00025
        score = c["fast_score"] + inside_penalty

        item = dict(c)
        item["inside_count"] = inside
        item["score"] = float(score)
        refined.append(item)

    refined.sort(key=lambda x: x["score"])
    best = refined[0]

    print(
        "[FOHO_F3_4_STAGE_B_SMOOTH_COLLISION] "
        f"evaluated={len(refined)} "
        f"best_inside={best.get('inside_count')} "
        f"best_score={best['score']:.6f}"
    )

    best_hv = hv0 + np.asarray(best["hand_translation_m"])
    best_ov = ov0 + np.asarray(best["object_translation_m"])

    final_hand = make_mesh_like(hand, best_hv)
    final_obj = make_mesh_like(obj, best_ov)

    out_root = Path(cfg.get("FOHO_F3_4_OUT_ROOT") or Path(cfg.get("BASE_DIR", ".")).joinpath("f3_4_mesh_refine"))
    out_root.mkdir(parents=True, exist_ok=True)

    hand_out = out_root / "final_hand_mesh.ply"
    obj_out = out_root / "final_obj_mesh.ply"
    json_out = out_root / "F3_4_mesh_refine_metrics.json"
    glb_out = out_root / "F3_4_same_frame_audit.glb"

    final_hand.export(hand_out)
    final_obj.export(obj_out)

    target_points = best_ov[target_ids]

    scene = trimesh.Scene()
    scene.add_geometry(color_mesh(final_obj, [90, 135, 240, 210]), node_name="gate_a_laptop_whole_object")
    scene.add_geometry(color_mesh(final_hand, [245, 120, 110, 220]), node_name="f3_4_hand")

    diag = float(np.linalg.norm(np.asarray(final_obj.bounds[1]) - np.asarray(final_obj.bounds[0])))
    radius = max(0.002, diag * 0.006)

    for i, p in enumerate(target_points):
        scene.add_geometry(marker(p, radius, [60, 220, 90, 255]), node_name=f"target_{i:02d}")

    for name, rgba in {
        "index": [255, 225, 40, 255],
        "middle": [255, 145, 35, 255],
        "pinky": [40, 220, 230, 255],
    }.items():
        scene.add_geometry(marker(best_hv[tip_ids[name]], radius * 1.4, rgba), node_name=f"{name}_tip")

    scene.export(glb_out)

    report = {
        "status": "completed",
        "input": {
            "hand": str(hand_path),
            "object": str(obj_path),
            "target_contract": str(target_contract_path),
        },
        "output": {
            "hand": str(hand_out),
            "object": str(obj_out),
            "json": str(json_out),
            "glb": str(glb_out),
        },
        "best": best,
        "references": {
            "f3_2_zero_update_inside_count": 617,
            "f3_2_s5c5_inside_count": 818,
            "f3_2_best_rigid_probe_inside_count": 769,
            "f3_3_v7_inside_count": 1241,
        },
        "object_integrity_policy": {
            "object_regenerated": False,
            "object_topology_preserved": True,
            "object_vertex_count_preserved": len(final_obj.vertices) == len(obj.vertices),
            "object_face_count_preserved": len(final_obj.faces) == len(obj.faces),
            "object_transform_type": "whole_object_translation_only",
            "lid_hinge_enabled": False,
            "internal_selector_disabled": selector_state == "0",
        },
    }

    json_out.write_text(json.dumps(report, indent=2) + "\n")

    print(f"[PASS] F3_4_FINAL_HAND={hand_out}")
    print(f"[PASS] F3_4_FINAL_OBJECT={obj_out}")
    print(f"[PASS] F3_4_AUDIT_JSON_WRITTEN={json_out}")
    print(f"[PASS] F3_4_AUDIT_GLB_WRITTEN={glb_out}")
    print("[FOHO_F3_4_FINAL_AUDIT_READY]")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception as exc:
        print(f"[HOLD] F3_4_BRANCH_FAILED={type(exc).__name__}: {exc}")
