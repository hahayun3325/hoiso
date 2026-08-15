from pathlib import Path
import itertools
import json
import os
import sys

try:
    import numpy as np
    import trimesh
    from scipy.spatial import cKDTree
    from scipy.spatial.transform import Rotation
except Exception as exc:
    print(f"[HOLD] F3_4B_IMPORT_FAILED={type(exc).__name__}: {exc}")
    np = trimesh = cKDTree = Rotation = None


TIP_IDS = {
    "thumb": 744,
    "index": 320,
    "middle": 443,
    "ring": 554,
    "pinky": 671,
}


def get_arg(argv, name, default=""):
    if name in argv:
        index = argv.index(name)
        if index + 1 < len(argv):
            return argv[index + 1]
    return default


def parse_env(path):
    data = {}
    p = Path(path)

    if not p.is_file():
        return data

    for raw in p.read_text().splitlines():
        line = raw.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")

    return data


def cfg_value(cfg, key, default=""):
    return os.environ.get(key, cfg.get(key, default))


def as_float(value, default):
    try:
        return float(value)
    except Exception:
        return float(default)


def as_int(value, default):
    try:
        return int(value)
    except Exception:
        return int(default)


def as_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def load_mesh(path):
    mesh = trimesh.load_mesh(path, process=False)

    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

    return mesh


def adjacency(vertex_count, faces):
    graph = [set() for _ in range(vertex_count)]

    for a, b, c in np.asarray(faces, dtype=np.int64):
        graph[a].update((b, c))
        graph[b].update((a, c))
        graph[c].update((a, b))

    return graph


def k_ring(graph, seed, hops):
    visited = {int(seed)}
    frontier = {int(seed)}

    for _ in range(hops):
        next_frontier = set()

        for vertex in frontier:
            next_frontier.update(graph[vertex])

        next_frontier -= visited
        visited.update(next_frontier)
        frontier = next_frontier

    return np.asarray(sorted(visited), dtype=np.int64)


def transform_vertices(vertices, translation, rotation_deg, center):
    matrix = Rotation.from_euler(
        "xyz",
        rotation_deg,
        degrees=True,
    ).as_matrix()

    return (
        (vertices - center) @ matrix.T
        + center
        + np.asarray(translation, dtype=np.float64)
    )


def contact_metrics(hand_vertices, target_points, contact_patch_ids):
    tree = cKDTree(target_points)

    index_distance = float(
        tree.query(hand_vertices[TIP_IDS["index"]], k=1)[0]
    )
    middle_distance = float(
        tree.query(hand_vertices[TIP_IDS["middle"]], k=1)[0]
    )

    patch_distances = tree.query(
        hand_vertices[contact_patch_ids],
        k=1,
    )[0]

    keep = max(4, int(np.ceil(len(patch_distances) * 0.25)))
    patch_low_quartile = float(
        np.mean(np.sort(patch_distances)[:keep])
    )

    return {
        "index_distance_m": index_distance,
        "middle_distance_m": middle_distance,
        "contact_mean_m": 0.5 * (
            index_distance + middle_distance
        ),
        "patch_low_quartile_m": patch_low_quartile,
    }


def full_metrics(
    hand_vertices,
    hand_faces,
    object_vertices,
    target_points,
    contact_patch_ids,
    narrow_band,
):
    contact = contact_metrics(
        hand_vertices,
        target_points,
        contact_patch_ids,
    )

    hand_mesh = trimesh.Trimesh(
        vertices=hand_vertices,
        faces=hand_faces,
        process=False,
    )

    inside_count = None
    inside_ratio = None

    if hand_mesh.is_watertight:
        inside = np.asarray(
            hand_mesh.contains(object_vertices),
            dtype=bool,
        )
        inside_count = int(inside.sum())
        inside_ratio = float(inside.mean())
    else:
        inside = np.zeros(len(object_vertices), dtype=bool)

    distance_to_hand_vertices = cKDTree(hand_vertices).query(
        object_vertices,
        k=1,
    )[0]

    narrow_penalty = float(
        np.maximum(
            0.0,
            narrow_band - distance_to_hand_vertices,
        ).mean()
    )

    contact.update(
        {
            "inside_count": inside_count,
            "inside_ratio": inside_ratio,
            "narrow_band_penalty": narrow_penalty,
            "hand_is_watertight": bool(hand_mesh.is_watertight),
        }
    )

    return contact


def color_mesh(mesh, rgba):
    copy = mesh.copy()
    copy.visual.vertex_colors = np.tile(
        np.asarray(rgba, dtype=np.uint8),
        (len(copy.vertices), 1),
    )
    return copy


def marker(point, radius, rgba):
    sphere = trimesh.creation.icosphere(
        subdivisions=2,
        radius=radius,
    )
    sphere.apply_translation(point)
    sphere.visual.vertex_colors = np.tile(
        np.asarray(rgba, dtype=np.uint8),
        (len(sphere.vertices), 1),
    )
    return sphere


def export_scene(
    hand,
    obj,
    target_points,
    path,
):
    diagonal = float(
        np.linalg.norm(obj.bounds[1] - obj.bounds[0])
    )
    radius = max(0.002, diagonal * 0.006)

    scene = trimesh.Scene()
    scene.add_geometry(
        color_mesh(obj, [90, 135, 240, 210]),
        node_name="fixed_gate_a_object",
    )
    scene.add_geometry(
        color_mesh(hand, [245, 120, 110, 220]),
        node_name="f3_4b_hand",
    )

    for index, point in enumerate(target_points):
        scene.add_geometry(
            marker(point, radius, [60, 210, 100, 255]),
            node_name=f"target_{index:02d}",
        )

    colors = {
        "index": [255, 225, 40, 255],
        "middle": [255, 145, 35, 255],
        "pinky": [40, 220, 230, 255],
    }

    for name in ("index", "middle", "pinky"):
        scene.add_geometry(
            marker(
                np.asarray(hand.vertices)[TIP_IDS[name]],
                radius * 1.3,
                colors[name],
            ),
            node_name=f"{name}_tip",
        )

    scene.export(path)


def main():
    if np is None:
        return

    cfg_path = get_arg(sys.argv, "--config")
    cfg = parse_env(cfg_path)

    if not cfg:
        print(f"[HOLD] F3_4B_CONFIG_NOT_LOADED={cfg_path}")
        return

    enabled = as_bool(
        cfg_value(cfg, "FOHO_F3_4B_ENABLE", "0")
    )

    if not enabled:
        print("[HOLD] F3_4B_NOT_ENABLED")
        return

    contract_path = Path(
        cfg_value(
            cfg,
            "FOHO_F3_4B_TARGET_CONTRACT_JSON",
            "",
        )
    )
    hand_path = Path(
        cfg_value(cfg, "FOHO_F3_4B_INIT_HAND_PLY", "")
    )
    object_path = Path(
        cfg_value(cfg, "FOHO_F3_4B_INIT_OBJECT_PLY", "")
    )
    out_root = Path(
        cfg_value(cfg, "FOHO_F3_4B_OUT_ROOT", "")
    )

    missing = [
        str(path)
        for path in (contract_path, hand_path, object_path)
        if not path.is_file()
    ]

    if missing:
        print(f"[HOLD] F3_4B_INPUTS_MISSING={missing}")
        return

    out_root.mkdir(parents=True, exist_ok=True)

    print(
        "[FOHO_F3_4B_RUNTIME_CONTRACT] "
        f"config={cfg_path}"
    )
    print(
        "[FOHO_F3_4B_INIT_SELECTION] "
        f"hand={hand_path} object={object_path}"
    )
    print(
        "[FOHO_F3_4B_OBJECT_FIXED] "
        "object_root=0 selector=0 hinge=0"
    )

    contract = json.loads(contract_path.read_text())
    target_ids = np.asarray(
        contract.get("fixed_object_target_vertex_ids", []),
        dtype=np.int64,
    )

    hand = load_mesh(hand_path)
    obj = load_mesh(object_path)

    if (
        target_ids.size == 0
        or target_ids.min() < 0
        or target_ids.max() >= len(obj.vertices)
    ):
        print("[HOLD] F3_4B_TARGET_IDS_INVALID")
        return

    target_points = np.asarray(obj.vertices)[target_ids]

    graph = adjacency(len(hand.vertices), hand.faces)
    index_patch = k_ring(
        graph,
        TIP_IDS["index"],
        as_int(cfg_value(cfg, "FOHO_F3_4B_PATCH_HOPS", "2"), 2),
    )
    middle_patch = k_ring(
        graph,
        TIP_IDS["middle"],
        as_int(cfg_value(cfg, "FOHO_F3_4B_PATCH_HOPS", "2"), 2),
    )
    contact_patch_ids = np.unique(
        np.concatenate((index_patch, middle_patch))
    )

    baseline = full_metrics(
        np.asarray(hand.vertices),
        np.asarray(hand.faces),
        np.asarray(obj.vertices),
        target_points,
        contact_patch_ids,
        as_float(
            cfg_value(
                cfg,
                "FOHO_F3_4B_NARROW_BAND_M",
                "0.010",
            ),
            0.010,
        ),
    )

    print(
        "[FOHO_F3_4B_TARGET_PATCH_AUDIT] "
        f"targets={len(target_ids)} "
        f"hand_patch_vertices={len(contact_patch_ids)} "
        f"baseline_index={baseline['index_distance_m']:.6f} "
        f"baseline_middle={baseline['middle_distance_m']:.6f} "
        f"baseline_inside={baseline['inside_count']}"
    )

    preflight_glb = out_root / "F3_4b_preflight.glb"
    export_scene(hand, obj, target_points, preflight_glb)

    if as_bool(
        cfg_value(
            cfg,
            "FOHO_F3_4B_PREFLIGHT_ONLY",
            "0",
        )
    ):
        print(
            f"[PASS] F3_4B_PREFLIGHT_GLB_WRITTEN={preflight_glb}"
        )
        print("[PASS] F3_4B_PREFLIGHT_READY")
        return

    max_translation = as_float(
        cfg_value(
            cfg,
            "FOHO_F3_4B_MAX_HAND_TRANS_M",
            "0.040",
        ),
        0.040,
    )
    max_rotation = as_float(
        cfg_value(
            cfg,
            "FOHO_F3_4B_MAX_HAND_ROT_DEG",
            "5.0",
        ),
        5.0,
    )
    contact_tolerance = as_float(
        cfg_value(
            cfg,
            "FOHO_F3_4B_CONTACT_REGRESSION_TOL_M",
            "0.010",
        ),
        0.010,
    )
    narrow_band = as_float(
        cfg_value(
            cfg,
            "FOHO_F3_4B_NARROW_BAND_M",
            "0.010",
        ),
        0.010,
    )
    top_k = as_int(
        cfg_value(cfg, "FOHO_F3_4B_TOP_K", "80"),
        80,
    )

    print(
        "[FOHO_F3_4B_BOUNDED_DOF_CONTRACT] "
        f"hand_trans_m={max_translation} "
        f"hand_rot_deg={max_rotation} "
        "object_trans_m=0 object_rot_deg=0"
    )

    hand_vertices = np.asarray(hand.vertices)
    center = hand_vertices.mean(axis=0)

    contact_center = hand_vertices[contact_patch_ids].mean(axis=0)
    target_center = target_points.mean(axis=0)
    direct_delta = target_center - contact_center

    delta_norm = float(np.linalg.norm(direct_delta))

    if delta_norm > max_translation and delta_norm > 0:
        direct_delta *= max_translation / delta_norm

    translations = {
        (0.0, 0.0, 0.0),
    }

    for fraction in (0.25, 0.50, 0.75, 1.0):
        translations.add(
            tuple(np.round(direct_delta * fraction, 8))
        )

    for translation in itertools.product(
        (-max_translation, 0.0, max_translation),
        repeat=3,
    ):
        translations.add(tuple(translation))

    rotations = list(
        itertools.product(
            (-max_rotation, 0.0, max_rotation),
            repeat=3,
        )
    )

    stage_a = []

    for translation in translations:
        for rotation in rotations:
            transformed = transform_vertices(
                hand_vertices,
                translation,
                rotation,
                center,
            )

            metrics = contact_metrics(
                transformed,
                target_points,
                contact_patch_ids,
            )

            transform_size = (
                np.linalg.norm(translation)
                / max(max_translation, 1e-8)
                + np.linalg.norm(rotation)
                / max(max_rotation, 1e-8)
            )

            score = (
                metrics["contact_mean_m"]
                + 0.5 * metrics["patch_low_quartile_m"]
                + 0.002 * transform_size
            )

            stage_a.append(
                {
                    "translation": tuple(translation),
                    "rotation": tuple(rotation),
                    "vertices": transformed,
                    "score": float(score),
                    **metrics,
                }
            )

    stage_a.sort(key=lambda item: item["score"])
    finalists = stage_a[: min(top_k, len(stage_a))]

    print(
        "[FOHO_F3_4B_STAGE_A_CONTACT_FIT] "
        f"evaluated={len(stage_a)} "
        f"best_index={finalists[0]['index_distance_m']:.6f} "
        f"best_middle={finalists[0]['middle_distance_m']:.6f}"
    )

    contact_limit = (
        baseline["contact_mean_m"] + contact_tolerance
    )

    stage_b = []

    for candidate in finalists:
        metrics = full_metrics(
            candidate["vertices"],
            np.asarray(hand.faces),
            np.asarray(obj.vertices),
            target_points,
            contact_patch_ids,
            narrow_band,
        )

        feasible = (
            metrics["contact_mean_m"] <= contact_limit
        )

        transform_size = (
            np.linalg.norm(candidate["translation"])
            + 0.002
            * np.linalg.norm(candidate["rotation"])
        )

        rank = (
            0 if feasible else 1,
            10**9
            if metrics["inside_count"] is None
            else metrics["inside_count"],
            metrics["narrow_band_penalty"],
            metrics["contact_mean_m"],
            transform_size,
        )

        stage_b.append(
            {
                **candidate,
                **metrics,
                "contact_feasible": feasible,
                "rank": rank,
            }
        )

    stage_b.sort(key=lambda item: item["rank"])
    best = stage_b[0]

    feasible_count = sum(
        bool(item["contact_feasible"])
        for item in stage_b
    )

    print(
        "[FOHO_F3_4B_CONTACT_FEASIBILITY_GATE] "
        f"limit={contact_limit:.6f} "
        f"feasible={feasible_count}/{len(stage_b)}"
    )
    print(
        "[FOHO_F3_4B_STAGE_B_COLLISION_FILTER] "
        f"best_inside={best['inside_count']} "
        f"best_index={best['index_distance_m']:.6f} "
        f"best_middle={best['middle_distance_m']:.6f}"
    )

    final_hand = hand.copy()
    final_hand.vertices = best["vertices"]

    final_object = obj.copy()

    hand_out = out_root / "final_hand_mesh.ply"
    object_out = out_root / "final_obj_mesh.ply"
    audit_json = out_root / "F3_4b_metrics.json"
    audit_glb = out_root / "F3_4b_same_frame_audit.glb"

    final_hand.export(hand_out)
    final_object.export(object_out)
    export_scene(
        final_hand,
        final_object,
        target_points,
        audit_glb,
    )

    report = {
        "input": {
            "hand": str(hand_path),
            "object": str(object_path),
            "target_contract": str(contract_path),
        },
        "output": {
            "hand": str(hand_out),
            "object": str(object_out),
            "audit_glb": str(audit_glb),
        },
        "baseline": baseline,
        "best": {
            key: value
            for key, value in best.items()
            if key not in {"vertices", "rank"}
        },
        "policy": {
            "object_fixed": True,
            "selector_disabled": True,
            "hinge_enabled": False,
            "contact_limit_m": contact_limit,
        },
    }

    audit_json.write_text(
        json.dumps(report, indent=2) + "\n"
    )

    print(
        "[FOHO_F3_4B_FINAL_METRICS] "
        f"index={best['index_distance_m']:.6f} "
        f"middle={best['middle_distance_m']:.6f} "
        f"inside={best['inside_count']}"
    )
    print(f"[PASS] F3_4B_FINAL_HAND={hand_out}")
    print(f"[PASS] F3_4B_FINAL_OBJECT={object_out}")
    print(f"[PASS] F3_4B_AUDIT_JSON={audit_json}")
    print(f"[PASS] F3_4B_AUDIT_GLB={audit_glb}")
    print("[FOHO_F3_4B_FINAL_AUDIT_READY]")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            f"[HOLD] F3_4B_RUNTIME_FAILED="
            f"{type(exc).__name__}: {exc}"
        )
