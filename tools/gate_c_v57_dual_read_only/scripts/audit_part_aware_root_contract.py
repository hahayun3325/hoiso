#!/usr/bin/env python3
"""Read-only, provenance-first audit of pre/post Gate-A object root state.

The script distinguishes exact lineage identity from geometric similarity.
A sampled surface fit is diagnostic only and cannot prove that Gate A preserved
or changed the source frame. Scene graph transforms are applied before audit.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_world_mesh(path: Path) -> tuple[trimesh.Trimesh, dict]:
    loaded = trimesh.load(path, process=False)
    info = {"type": type(loaded).__name__, "scene_nodes": []}
    if isinstance(loaded, trimesh.Scene):
        for node in loaded.graph.nodes_geometry:
            transform, geom_name = loaded.graph[node]
            info["scene_nodes"].append({
                "node": str(node),
                "geometry": str(geom_name),
                "transform": np.asarray(transform, dtype=float).tolist(),
            })
        world = loaded.dump(concatenate=True)
        if isinstance(world, list):
            meshes = [m for m in world if isinstance(m, trimesh.Trimesh)]
            if not meshes:
                raise ValueError(f"no_mesh_geometry:{path}")
            world = trimesh.util.concatenate(meshes)
        loaded = world
    if not isinstance(loaded, trimesh.Trimesh):
        raise TypeError(f"not_a_mesh:{path}")
    if len(loaded.vertices) == 0 or len(loaded.faces) == 0:
        raise ValueError(f"empty_mesh:{path}")
    return loaded, info


def umeyama(source: np.ndarray, target: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    if source.shape != target.shape or source.ndim != 2 or source.shape[1] != 3:
        raise ValueError("umeyama_requires_matching_Nx3_arrays")
    src_mean = source.mean(axis=0)
    tgt_mean = target.mean(axis=0)
    src_c = source - src_mean
    tgt_c = target - tgt_mean
    cov = tgt_c.T @ src_c / max(len(source), 1)
    u, singular, vt = np.linalg.svd(cov)
    correction = np.eye(3)
    if np.linalg.det(u @ vt) < 0:
        correction[-1, -1] = -1
    rotation = u @ correction @ vt
    variance = float(np.mean(np.sum(src_c * src_c, axis=1)))
    scale = float(np.trace(np.diag(singular) @ correction) / max(variance, 1e-18))
    translation = tgt_mean - scale * (rotation @ src_mean)
    return scale, rotation, translation


def transform(points: np.ndarray, scale: float, rotation: np.ndarray, translation: np.ndarray) -> np.ndarray:
    return scale * (points @ rotation.T) + translation


def rotation_angle_deg(rotation: np.ndarray) -> float:
    cosv = float(np.clip((np.trace(rotation) - 1.0) / 2.0, -1.0, 1.0))
    return math.degrees(math.acos(cosv))


def deterministic_surface(mesh: trimesh.Trimesh, count: int, seed: int) -> np.ndarray:
    points, _ = trimesh.sample.sample_surface(mesh, count=count, seed=seed)
    return np.asarray(points, dtype=np.float64)


def load_correspondence(path: Path) -> np.ndarray:
    if path.suffix.lower() == ".npy":
        arr = np.load(path)
    else:
        arr = np.loadtxt(path, delimiter="," if path.suffix.lower() == ".csv" else None, dtype=int)
    arr = np.asarray(arr, dtype=np.int64)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError("correspondence_must_be_Nx2")
    return arr


def summarize_distances(d: np.ndarray) -> dict:
    return {
        "mean": float(np.mean(d)),
        "rmse": float(np.sqrt(np.mean(d * d))),
        "p95": float(np.percentile(d, 95)),
        "max": float(np.max(d)),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--thresholds", required=True)
    p.add_argument("--correspondence", default="")
    p.add_argument("--lineage-mode", choices=["unknown", "fixed_partition", "candidate_substitution"], default="unknown")
    p.add_argument("--samples", type=int, default=30000)
    p.add_argument("--iterations", type=int, default=20)
    p.add_argument("--seed", type=int, default=1234)
    args = p.parse_args()

    source_path, target_path = Path(args.source), Path(args.target)
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "part_aware_root_contract_audit_v2",
        "source": str(source_path), "target": str(target_path),
        "lineage_mode": args.lineage_mode,
        "authorizes_nonzero_work": False,
    }
    try:
        thresholds = json.loads(Path(args.thresholds).read_text(encoding="utf-8"))
        src, src_scene = load_world_mesh(source_path)
        tgt, tgt_scene = load_world_mesh(target_path)
        src_v = np.asarray(src.vertices, dtype=np.float64)
        tgt_v = np.asarray(tgt.vertices, dtype=np.float64)
        target_diag = float(max(np.linalg.norm(np.asarray(tgt.extents, dtype=float)), 1e-12))
        report.update(
            status="COMPLETE",
            source_sha256=sha256(source_path), target_sha256=sha256(target_path),
            source_scene=src_scene, target_scene=tgt_scene,
            source_counts={"vertices": int(len(src.vertices)), "faces": int(len(src.faces))},
            target_counts={"vertices": int(len(tgt.vertices)), "faces": int(len(tgt.faces))},
            source_centroid=np.asarray(src.centroid, dtype=float).tolist(),
            target_centroid=np.asarray(tgt.centroid, dtype=float).tolist(),
            source_extents=np.asarray(src.extents, dtype=float).tolist(),
            target_extents=np.asarray(tgt.extents, dtype=float).tolist(),
            target_diagonal=target_diag,
        )

        correspondence = None
        correspondence_basis = "none"
        if args.correspondence:
            correspondence = load_correspondence(Path(args.correspondence))
            if np.any(correspondence[:, 0] < 0) or np.any(correspondence[:, 0] >= len(src_v)):
                raise IndexError("source_correspondence_out_of_range")
            if np.any(correspondence[:, 1] < 0) or np.any(correspondence[:, 1] >= len(tgt_v)):
                raise IndexError("target_correspondence_out_of_range")
            correspondence_basis = "explicit_vertex_map"
        elif args.lineage_mode == "fixed_partition" and len(src_v) == len(tgt_v):
            correspondence = np.column_stack([np.arange(len(src_v)), np.arange(len(tgt_v))])
            correspondence_basis = "same_index_assumption_from_fixed_partition"

        direct = None
        fit_basis = "sampled_surface_nearest_neighbor"
        if correspondence is not None:
            s = src_v[correspondence[:, 0]]
            t = tgt_v[correspondence[:, 1]]
            raw_delta = np.linalg.norm(s - t, axis=1)
            scale, rotation, translation = umeyama(s, t)
            moved = transform(s, scale, rotation, translation)
            fit_delta = np.linalg.norm(moved - t, axis=1)
            direct = {
                "basis": correspondence_basis,
                "count": int(len(correspondence)),
                "raw": summarize_distances(raw_delta),
                "after_similarity": summarize_distances(fit_delta),
            }
            fit_basis = correspondence_basis
        else:
            src_p = deterministic_surface(src, args.samples, args.seed)
            tgt_p = deterministic_surface(tgt, args.samples, args.seed + 1)
            scale = 1.0
            rotation = np.eye(3)
            translation = tgt_p.mean(axis=0) - src_p.mean(axis=0)
            tgt_tree = cKDTree(tgt_p)
            for _ in range(args.iterations):
                moved = transform(src_p, scale, rotation, translation)
                _, indices = tgt_tree.query(moved, k=1)
                matched = tgt_p[indices]
                ds, dr, dt = umeyama(moved, matched)
                scale = ds * scale
                rotation = dr @ rotation
                translation = ds * (dr @ translation) + dt

        matrix = np.eye(4)
        matrix[:3, :3] = scale * rotation
        matrix[:3, 3] = translation
        rotation_deg = rotation_angle_deg(rotation)
        translation_norm = float(np.linalg.norm(translation))

        src_points = deterministic_surface(src, args.samples, args.seed + 2)
        tgt_points = deterministic_surface(tgt, args.samples, args.seed + 3)
        moved_src = transform(src_points, scale, rotation, translation)
        tgt_tree = cKDTree(tgt_points)
        src_tree = cKDTree(moved_src)
        d_st, _ = tgt_tree.query(moved_src, k=1)
        d_ts, _ = src_tree.query(tgt_points, k=1)
        eq = thresholds["geometric_equivalence"]
        coverage_distance = float(eq["bidirectional_coverage_distance_over_target_diagonal"] * target_diag)
        symmetric = {
            "source_to_target": summarize_distances(d_st),
            "target_to_source": summarize_distances(d_ts),
            "rmse": float(np.sqrt((np.mean(d_st*d_st) + np.mean(d_ts*d_ts)) / 2.0)),
            "p95": float(max(np.percentile(d_st, 95), np.percentile(d_ts, 95))),
            "coverage_source_to_target": float(np.mean(d_st <= coverage_distance)),
            "coverage_target_to_source": float(np.mean(d_ts <= coverage_distance)),
            "coverage_distance": coverage_distance,
        }
        report["direct_correspondence"] = direct
        report["best_fit_similarity"] = {
            "basis": fit_basis,
            "scale": float(scale),
            "rotation": rotation.tolist(),
            "rotation_deg": rotation_deg,
            "translation": translation.tolist(),
            "translation_norm": translation_norm,
            "translation_over_target_diagonal": translation_norm / target_diag,
            "matrix": matrix.tolist(),
        }
        report["symmetric_surface"] = symmetric

        strict = thresholds["strict_identity"]
        identity_transform = (
            abs(scale - 1.0) <= strict["scale_abs_error_max"] and
            rotation_deg <= strict["rotation_deg_max"] and
            translation_norm / target_diag <= strict["translation_over_target_diagonal_max"]
        )
        sampled_geometric_equivalent = (
            symmetric["rmse"] / target_diag <= eq["symmetric_rmse_over_target_diagonal_max"] and
            symmetric["p95"] / target_diag <= eq["symmetric_p95_over_target_diagonal_max"] and
            min(symmetric["coverage_source_to_target"], symmetric["coverage_target_to_source"]) >= eq["bidirectional_coverage_min"]
        )
        mapped_identity = False
        mapped_similarity_equivalent = False
        if direct is not None:
            mapped_identity = (
                direct["raw"]["rmse"] / target_diag <= strict["mapped_vertex_rmse_over_target_diagonal_max"] and
                direct["raw"]["max"] / target_diag <= strict["mapped_vertex_max_over_target_diagonal_max"]
            )
            mapped_similarity_equivalent = (
                direct["after_similarity"]["rmse"] / target_diag <= strict["mapped_vertex_rmse_over_target_diagonal_max"] and
                direct["after_similarity"]["max"] / target_diag <= strict["mapped_vertex_max_over_target_diagonal_max"]
            )
        geometric_equivalent = mapped_similarity_equivalent if direct is not None else sampled_geometric_equivalent

        if args.lineage_mode == "fixed_partition" and direct is not None and mapped_identity and identity_transform:
            classification = "ROOT_IDENTITY_CONFIRMED"
        elif geometric_equivalent and not identity_transform:
            classification = "SAME_GEOMETRY_NONIDENTITY_ROOT"
        elif not geometric_equivalent:
            classification = "GEOMETRY_OR_CANDIDATE_CHANGED"
        else:
            classification = "AMBIGUOUS_NO_PROVEN_VERTEX_LINEAGE"
        report["classification"] = classification
        report["checks"] = {
            "identity_transform": identity_transform,
            "geometric_equivalent": geometric_equivalent,
            "sampled_geometric_equivalent": sampled_geometric_equivalent,
            "mapped_similarity_equivalent": mapped_similarity_equivalent,
            "mapped_identity": mapped_identity,
        }
        report["interpretation"] = {
            "ROOT_IDENTITY_CONFIRMED": "Gate A preserved the root under the supplied fixed-partition lineage evidence.",
            "SAME_GEOMETRY_NONIDENTITY_ROOT": "The geometry is explainable by one similarity, but the root changed. Determine whether this is an export/assembly bug or a new normalized candidate before applying a correction.",
            "GEOMETRY_OR_CANDIDATE_CHANGED": "One similarity does not explain the difference. Bind the accepted candidate and estimate its own metric root; the old hand-object transform is obsolete.",
            "AMBIGUOUS_NO_PROVEN_VERTEX_LINEAGE": "The geometric fit is near identity, but source lineage is insufficient to prove that Gate A preserved the root. Recover the vertex map or source manifest.",
        }[classification]

        aligned = src.copy(); aligned.apply_transform(matrix)
        aligned.export(out / "source_aligned_to_target.ply")
    except Exception as exc:
        report.update(status="HOLD", classification="AUDIT_ERROR", error=f"{type(exc).__name__}:{exc}")

    (out / "root_contract_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Part-aware object-root contract audit",
        "",
        f"**Status:** `{report.get('status')}`",
        f"**Classification:** `{report.get('classification')}`",
        "",
        report.get("interpretation", report.get("error", "")),
        "",
        "This report is read-only and does not authorize a transform or optimizer.",
    ]
    (out / "root_contract_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report.get("status") == "COMPLETE" else 1

if __name__ == "__main__":
    raise SystemExit(main())
