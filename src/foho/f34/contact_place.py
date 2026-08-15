from pathlib import Path
import itertools
import json
import os
import sys

try:
    import numpy as np
    import trimesh
    from scipy.spatial import cKDTree
except Exception as exc:
    print(f"[HOLD] F3_4_IMPORT_FAILED={type(exc).__name__}: {exc}")
    np = None


def arg_value(argv, key, default=""):
    if key in argv:
        i = argv.index(key)
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
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data


def as_bool(v):
    return str(v).lower() in {"1", "true", "yes", "on"}


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


def color_mesh(mesh, rgba):
    out = mesh.copy()
    out.visual.vertex_colors = np.tile(np.asarray(rgba, dtype=np.uint8), (len(out.vertices), 1))
    return out


def marker(point, radius, rgba):
    s = trimesh.creation.icosphere(subdivisions=2, radius=radius)
    s.apply_translation(point)
    s.visual.vertex_colors = np.tile(np.asarray(rgba, dtype=np.uint8), (len(s.vertices), 1))
    return s


def main(argv):
    if np is None:
        return

    cfg_path = arg_value(argv, "--config")
    preflight = "--preflight" in argv

    cfg = parse_env(cfg_path)
    if not cfg:
        return

    enabled = as_bool(os.environ.get("FOHO_F3_4_ENABLE", cfg.get("FOHO_F3_4_ENABLE", "0")))
    if not enabled:
        print("[HOLD] F3_4_NOT_ENABLED")
        return

    selector = os.environ.get(
        "FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR",
        cfg.get("FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR", "0"),
    )
    hinge = cfg.get("FOHO_F3_4_OPT_LID_HINGE", "0")

    print(f"[FOHO_F3_4_RUNTIME_CONTRACT] config={cfg_path}")
    print(f"[FOHO_F3_4_SELECTOR_DISABLED] FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR={selector}")
    print(f"[FOHO_F3_4_HINGE_POLICY] first_trial_lid_hinge={hinge}")

    if selector != "0":
        print("[HOLD] F3_4_SELECTOR_MUST_BE_DISABLED")
        return

    if hinge not in {"0", "false", "False", "off", "OFF"}:
        print("[HOLD] F3_4_LID_HINGE_DISABLED_FOR_FIRST_CONTACT_PLACEMENT_TRIAL")
        return

    target_contract_path = Path(cfg.get("FOHO_F3_4_TARGET_CONTRACT_JSON", ""))
    side_contract_path = Path(cfg.get("FOHO_F3_4_SIDE_CONTRACT_JSON", ""))

    if not target_contract_path.is_file():
        print(f"[HOLD] F3_4_TARGET_CONTRACT_MISSING={target_contract_path}")
        return

    if not side_contract_path.is_file():
        print(f"[HOLD] F3_4_SIDE_CONTRACT_MISSING={side_contract_path}")
        return

    try:
        target_contract = json.loads(target_contract_path.read_text())
        side_contract = json.loads(side_contract_path.read_text())
    except Exception as exc:
        print(f"[HOLD] F3_4_CONTRACT_READ_FAILED={type(exc).__name__}: {exc}")
        return

    print(f"[FOHO_F3_4_TARGET_FRAME_CONTRACT] json={target_contract_path}")
    print(f"[FOHO_F3_4_CONTACT_SIDE_CONTRACT] json={side_contract_path}")

    max_hand_t = as_float(cfg.get("FOHO_F3_4_MAX_HAND_TRANS_M", "0.12"), 0.12)
    max_obj_t = as_float(cfg.get("FOHO_F3_4_MAX_OBJECT_TRANS_M", "0.02"), 0.02)

    print(
        "[FOHO_F3_4_BOUNDED_DOF_CONTRACT] "
        f"hand_translation_m={max_hand_t} object_translation_m={max_obj_t} "
        "rotation_disabled_first_trial=1 object_regen_disabled=1"
    )

    if preflight:
        print("[PASS] F3_4_PREFLIGHT_READY")
        return

    hand_path = cfg.get("FOHO_F3_4_INIT_HAND_PLY") or target_contract.get("hand_path", "")
    obj_path = cfg.get("FOHO_F3_4_INIT_OBJECT_PLY") or target_contract.get("final_object_path", "")

    hand = load_mesh(hand_path)
    obj = load_mesh(obj_path)
    if hand is None or obj is None:
        return

    hv0 = np.asarray(hand.vertices, dtype=np.float64)
    ov0 = np.asarray(obj.vertices, dtype=np.float64)

    target_ids = np.asarray(target_contract.get("fixed_object_target_vertex_ids", []), dtype=np.int64)
    if target_ids.size == 0 or target_ids.max() >= len(ov0):
        print("[HOLD] F3_4_TARGET_IDS_INVALID")
        return

    target_center = np.asarray(side_contract["target_center"], dtype=np.float64)
    target_normal = np.asarray(side_contract["contact_side_normal"], dtype=np.float64)
    target_normal = target_normal / (np.linalg.norm(target_normal) + 1e-9)

    tip_ids = {"index": 320, "middle": 443, "pinky": 671}
    if max(tip_ids.values()) >= len(hv0):
        print("[HOLD] F3_4_HAND_TIP_IDS_INVALID")
        return

    target_points0 = ov0[target_ids]

    # Compute direct contact-placement seed:
    # move index/middle centroid close to lid target center, slightly on contact side.
    tip_center0 = 0.5 * (hv0[tip_ids["index"]] + hv0[tip_ids["middle"]])
    contact_seed = target_center + 0.004 * target_normal - tip_center0

    obj_normals = np.asarray(obj.vertex_normals)
    if len(obj_normals) != len(ov0):
        obj_normals = np.zeros_like(ov0)

    def eval_candidate(hand_t, obj_t):
        hv = hv0 + hand_t
        ov = ov0 + obj_t
        targets = target_points0 + obj_t

        target_tree = cKDTree(targets)
        index_d = float(target_tree.query(hv[tip_ids["index"]], k=1)[0])
        middle_d = float(target_tree.query(hv[tip_ids["middle"]], k=1)[0])
        contact = 0.5 * (index_d + middle_d)

        center = target_center + obj_t
        side_index = float(np.dot(hv[tip_ids["index"]] - center, target_normal))
        side_middle = float(np.dot(hv[tip_ids["middle"]] - center, target_normal))
        side_penalty = max(0.0, 0.002 - side_index) + max(0.0, 0.002 - side_middle)

        object_tree = cKDTree(ov)
        d_hand_obj, nn = object_tree.query(hv, k=1)
        p5 = float(np.percentile(d_hand_obj, 5))
        proximity_penalty = abs(p5 - 0.006)

        # Soft open-surface guard only; this is not a hard watertight collision test.
        nearest_normals = obj_normals[nn]
        q = ov[nn]
        signed = np.sum((hv - q) * nearest_normals, axis=1)
        soft_collision = float(np.mean(np.maximum(0.0, -signed - 0.005)))

        # Strong transform regularization.
        reg = 0.03 * float(np.linalg.norm(hand_t)) + 0.50 * float(np.linalg.norm(obj_t))

        score = (
            1.0 * contact
            + 5.0 * side_penalty
            + 0.5 * proximity_penalty
            + 1.0 * soft_collision
            + reg
        )

        return {
            "score": float(score),
            "index_distance_m": index_d,
            "middle_distance_m": middle_d,
            "side_index_m": side_index,
            "side_middle_m": side_middle,
            "p5_hand_object_distance_m": p5,
            "soft_collision_penalty": soft_collision,
        }

    # Search around the direct contact seed.
    offsets = [-0.030, -0.015, 0.0, 0.015, 0.030]
    obj_offsets = [-max_obj_t, 0.0, max_obj_t] if max_obj_t > 0 else [0.0]

    candidates = []
    for dx, dy, dz in itertools.product(offsets, offsets, offsets):
        hand_t = contact_seed + np.asarray([dx, dy, dz], dtype=np.float64)

        # Optional clamp to avoid absurd jumps.
        norm = np.linalg.norm(hand_t)
        if norm > max_hand_t:
            hand_t = hand_t / (norm + 1e-9) * max_hand_t

        for ox, oy, oz in itertools.product(obj_offsets, obj_offsets, obj_offsets):
            obj_t = np.asarray([ox, oy, oz], dtype=np.float64)
            metrics = eval_candidate(hand_t, obj_t)
            metrics["hand_translation_m"] = hand_t.tolist()
            metrics["object_translation_m"] = obj_t.tolist()
            candidates.append(metrics)

    candidates.sort(key=lambda x: x["score"])
    best = candidates[0]

    print(
        "[FOHO_F3_4_STAGE_A_CONTACT_PLACEMENT] "
        f"best_index={best['index_distance_m']:.6f} "
        f"best_middle={best['middle_distance_m']:.6f} "
        f"score={best['score']:.6f}"
    )

    print(
        "[FOHO_F3_4_STAGE_B_SOFT_OPEN_SURFACE_COLLISION] "
        f"soft_collision_penalty={best['soft_collision_penalty']:.6f} "
        f"p5={best['p5_hand_object_distance_m']:.6f}"
    )

    hand_t = np.asarray(best["hand_translation_m"])
    obj_t = np.asarray(best["object_translation_m"])

    final_hand = make_mesh_like(hand, hv0 + hand_t)
    final_obj = make_mesh_like(obj, ov0 + obj_t)

    out_root = Path(cfg.get("FOHO_F3_4_OUT_ROOT", Path(cfg.get("BASE_DIR", ".")).joinpath("f3_4_contact_place")))
    out_root.mkdir(parents=True, exist_ok=True)

    hand_out = out_root / "final_hand_mesh.ply"
    obj_out = out_root / "final_obj_mesh.ply"
    json_out = out_root / "F3_4_contact_place_metrics.json"
    glb_out = out_root / "F3_4_contact_place_audit.glb"

    final_hand.export(hand_out)
    final_obj.export(obj_out)

    scene = trimesh.Scene()
    scene.add_geometry(color_mesh(final_obj, [90, 135, 240, 210]), node_name="gate_a_laptop_preserved")
    scene.add_geometry(color_mesh(final_hand, [245, 120, 110, 220]), node_name="f3_4_contact_placed_hand")

    diag = float(np.linalg.norm(np.asarray(final_obj.bounds[1]) - np.asarray(final_obj.bounds[0])))
    radius = max(0.002, diag * 0.006)

    target_points = target_points0 + obj_t
    for i, p in enumerate(target_points):
        scene.add_geometry(marker(p, radius, [60, 220, 90, 255]), node_name=f"target_{i:02d}")

    for name, rgba in {
        "index": [255, 225, 40, 255],
        "middle": [255, 145, 35, 255],
        "pinky": [40, 220, 230, 255],
    }.items():
        scene.add_geometry(marker(np.asarray(final_hand.vertices)[tip_ids[name]], radius * 1.4, rgba), node_name=f"{name}_tip")

    scene.export(glb_out)

    report = {
        "status": "completed",
        "input": {
            "hand": str(hand_path),
            "object": str(obj_path),
            "target_contract": str(target_contract_path),
            "side_contract": str(side_contract_path),
        },
        "output": {
            "hand": str(hand_out),
            "object": str(obj_out),
            "json": str(json_out),
            "glb": str(glb_out),
        },
        "best": best,
        "object_integrity_policy": {
            "object_regenerated": False,
            "object_topology_preserved": True,
            "object_vertex_count_preserved": len(final_obj.vertices) == len(obj.vertices),
            "object_face_count_preserved": len(final_obj.faces) == len(obj.faces),
            "lid_hinge_enabled": False,
            "internal_selector_disabled": selector == "0",
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
        print(f"[HOLD] F3_4_CONTACT_PLACE_FAILED={type(exc).__name__}: {exc}")
