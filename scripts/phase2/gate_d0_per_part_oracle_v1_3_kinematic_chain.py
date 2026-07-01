from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree


# Reuse tested utilities from v1.2.
V12_PATH = Path("scripts/phase2/gate_d0_per_part_oracle_v1_2_hinge_axis_refine.py")
spec = importlib.util.spec_from_file_location("v12", V12_PATH)
v12 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(v12)


def bbox_intersection_volume(bounds_a: np.ndarray, bounds_b: np.ndarray) -> float:
    lo = np.maximum(bounds_a[0], bounds_b[0])
    hi = np.minimum(bounds_a[1], bounds_b[1])
    extent = np.maximum(hi - lo, 0.0)
    return float(np.prod(extent))


def physical_interpart_scores(base: trimesh.Trimesh, screen: trimesh.Trimesh) -> dict:
    """
    Proxy physical score. This is not a perfect SDF penetration test.
    It catches obvious screen/base crossing and excessive overlap.

    Good laptop:
      - small hinge seam contact
      - low global overlap
      - screen mostly on one side of the base plane
    Bad laptop:
      - large AABB overlap
      - many points extremely close away from hinge
      - many screen points cross through base plane
    """
    b_pts = v12.sample_points(base, 12000, seed=700)
    s_pts = v12.sample_points(screen, 12000, seed=701)

    # Nearest-distance based overlap proxy.
    tree_b = cKDTree(b_pts)
    d_s2b, _ = tree_b.query(s_pts, k=1)

    near_2mm = float((d_s2b < 0.002).mean())
    near_5mm = float((d_s2b < 0.005).mean())
    near_10mm = float((d_s2b < 0.010).mean())

    # Hinge connection proxy: some near points are good, too many near points are bad.
    hinge_gap_p1 = float(np.percentile(d_s2b, 1))
    hinge_gap_p5 = float(np.percentile(d_s2b, 5))
    hinge_gap_mean = float(d_s2b.mean())

    # AABB overlap proxy.
    b_bounds = np.asarray(base.bounds, dtype=np.float64)
    s_bounds = np.asarray(screen.bounds, dtype=np.float64)
    inter_vol = bbox_intersection_volume(b_bounds, s_bounds)
    b_vol = float(np.prod(np.maximum(b_bounds[1] - b_bounds[0], 1e-12)))
    s_vol = float(np.prod(np.maximum(s_bounds[1] - s_bounds[0], 1e-12)))
    min_vol = max(min(b_vol, s_vol), 1e-12)
    bbox_overlap_ratio = inter_vol / min_vol

    # Base-plane crossing proxy.
    # Use PCA normal of base: smallest-variance axis.
    center, axes = v12.pca_axes(b_pts)
    normal = axes[-1]
    signed = (s_pts - center) @ normal

    # Screen should not straddle base plane too much.
    pos_ratio = float((signed > 0.0).mean())
    neg_ratio = float((signed < 0.0).mean())
    smaller_side_ratio = min(pos_ratio, neg_ratio)

    return {
        "near_fraction_2mm": near_2mm,
        "near_fraction_5mm": near_5mm,
        "near_fraction_10mm": near_10mm,
        "hinge_gap_p1": hinge_gap_p1,
        "hinge_gap_p5": hinge_gap_p5,
        "hinge_gap_mean": hinge_gap_mean,
        "bbox_overlap_ratio": bbox_overlap_ratio,
        "base_plane_screen_smaller_side_ratio": smaller_side_ratio,
        "note": "Proxy only. Later replace with SDF/interpenetration or renderer-based test."
    }


def make_boundary_axis_candidates(boundary: dict) -> list[dict]:
    center = boundary["center"]
    axes = boundary["axes"]
    main = boundary["axis"]

    candidates = []

    def add(name: str, axis: np.ndarray):
        axis = axis / max(np.linalg.norm(axis), 1e-12)
        candidates.append({"name": name, "axis": axis})
        candidates.append({"name": name + "_neg", "axis": -axis})

    # Main hinge from screen-base interface.
    add("boundary_interface_axis", main)

    # Small perturbations around interface axis, not free PCA axes.
    for i, a in enumerate(axes[1:3], start=1):
        a = a / max(np.linalg.norm(a), 1e-12)
        for eps in [-0.20, -0.10, 0.10, 0.20]:
            add(f"boundary_axis_perturb_pca{i}_{eps:+.2f}", main + eps * a)

    # Deduplicate axes up to sign.
    unique = []
    for c in candidates:
        keep = True
        for u in unique:
            if abs(float(np.dot(c["axis"], u["axis"]))) > 0.985:
                keep = False
                break
        if keep:
            unique.append(c)

    return unique


def make_boundary_center_candidates(boundary: dict, shared_scale: float) -> list[dict]:
    center = boundary["center"]
    axes = boundary["axes"]

    # Small offsets only. Large offsets caused v1.2 to choose physically odd hinges.
    step = 0.015 / max(shared_scale, 1e-6)
    offsets = [0.0, -step, step, -2 * step, 2 * step]

    cands = []
    for i, ax in enumerate(axes[:3]):
        ax = ax / max(np.linalg.norm(ax), 1e-12)
        for off in offsets:
            cands.append({
                "name": f"boundary_pca{i}_offset_{off:.4f}",
                "center": center + off * ax,
            })

    # Deduplicate.
    unique = []
    for c in cands:
        if not any(np.linalg.norm(c["center"] - u["center"]) < 1e-6 for u in unique):
            unique.append(c)
    return unique


def candidate_score(whole_metrics: dict, phys: dict, base_score: float, screen_score: float) -> float:
    bbox_vol = whole_metrics["bbox"]["bbox_volume_ratio_pred_over_gt"]

    # Want hinge connected but not entire parts overlapping.
    hinge_disconnect_penalty = max(0.0, phys["hinge_gap_p5"] - 0.015)
    excessive_near_penalty = max(0.0, phys["near_fraction_5mm"] - 0.20)
    bbox_overlap_penalty = max(0.0, phys["bbox_overlap_ratio"] - 0.35)
    plane_cross_penalty = max(0.0, phys["base_plane_screen_smaller_side_ratio"] - 0.20)

    score = (
        1.00 * whole_metrics["symmetric_mean"]
        + 0.30 * base_score
        + 0.30 * screen_score
        + 0.10 * abs(bbox_vol - 1.0)
        + 1.00 * hinge_disconnect_penalty
        + 1.50 * excessive_near_penalty
        + 0.75 * bbox_overlap_penalty
        + 0.50 * plane_cross_penalty
        + (10.0 if whole_metrics["collapse_flag"] else 0.0)
    )

    return float(score)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case-root", required=True)
    ap.add_argument("--n-points", type=int, default=20000)
    ap.add_argument("--iters", type=int, default=30)
    ap.add_argument("--angle-min", type=float, default=-120.0)
    ap.add_argument("--angle-max", type=float, default=120.0)
    ap.add_argument("--angle-step", type=float, default=5.0)
    ap.add_argument("--top-k", type=int, default=20)
    args = ap.parse_args()

    case_root = Path(args.case_root)
    part_dir = case_root / "part_meshes_partfield_v2_vmap"

    out_root = case_root / "gate_d0_object_repair/per_part_oracle_v1_3_kinematic_chain"
    out_mesh = out_root / "outputs"
    out_vis = out_root / "visuals"
    out_metrics = out_root / "metrics"
    for p in [out_mesh, out_vis, out_metrics]:
        p.mkdir(parents=True, exist_ok=True)

    screen = v12.load_mesh(part_dir / "screen.ply")
    base = v12.load_mesh(part_dir / "keyboard_base.ply")
    hinge_path = part_dir / "hinge.ply"
    hinge = v12.load_mesh(hinge_path) if hinge_path.exists() else None
    gt = v12.load_mesh(case_root / "gt_reference/selected/gt_object_mesh.ply")

    pred_union = trimesh.util.concatenate([base, screen] + ([hinge] if hinge is not None else []))
    T0, shared_scale = v12.shared_scale_init(pred_union, gt)

    # Pseudo-GT split only for oracle scoring.
    gt_pts = v12.sample_points(gt, args.n_points, seed=500)
    labels, _ = v12.kmeans2(gt_pts, n_iters=40)
    gt_clusters = [gt_pts[labels == 0], gt_pts[labels == 1]]

    boundary = v12.estimate_boundary_hinge(base, screen)
    axis_candidates = make_boundary_axis_candidates(boundary)
    center_candidates = make_boundary_center_candidates(boundary, shared_scale)

    angle_values = np.arange(args.angle_min, args.angle_max + 1e-6, args.angle_step)

    all_candidates = []

    for base_cluster_idx in [0, 1]:
        screen_cluster_idx = 1 - base_cluster_idx

        base_target = gt_clusters[base_cluster_idx]
        screen_target = gt_clusters[screen_cluster_idx]

        # Base root pose only. This is the only SE(3) root.
        T_base = v12.icp_no_scale_to_points(
            src_mesh=base,
            tgt_pts=base_target,
            T_init=T0,
            n_points=args.n_points,
            n_iters=args.iters,
            seed=900 + base_cluster_idx,
        )

        base_moved = base.copy()
        base_moved.apply_transform(T_base)

        hinge_moved = None
        if hinge is not None:
            hinge_moved = hinge.copy()
            hinge_moved.apply_transform(T_base)

        base_eval_pts = v12.sample_points(base_moved, max(5000, args.n_points // 2), seed=901)
        base_part_score = v12.symmetric_point_distance(base_eval_pts, base_target)["symmetric_mean"]

        for axis_c in axis_candidates:
            for center_c in center_candidates:
                axis = axis_c["axis"]
                center = center_c["center"]

                for angle_deg in angle_values:
                    # Kinematic chain:
                    # screen transform = base root transform composed with one revolute motion.
                    A = v12.rotation_about_axis(center, axis, math.radians(float(angle_deg)))
                    T_screen = T_base @ A

                    screen_moved = screen.copy()
                    screen_moved.apply_transform(T_screen)

                    parts = [base_moved, screen_moved]
                    if hinge_moved is not None:
                        parts.append(hinge_moved)

                    union = trimesh.util.concatenate(parts)

                    whole_metrics = v12.eval_mesh_pair(
                        f"kinematic_chain_angle_{angle_deg:.1f}_{axis_c['name']}_{center_c['name']}",
                        union,
                        gt,
                        args.n_points,
                    )

                    screen_eval_pts = v12.sample_points(screen_moved, max(5000, args.n_points // 2), seed=902)
                    screen_part_score = v12.symmetric_point_distance(screen_eval_pts, screen_target)["symmetric_mean"]

                    phys = physical_interpart_scores(base_moved, screen_moved)

                    score = candidate_score(
                        whole_metrics=whole_metrics,
                        phys=phys,
                        base_score=float(base_part_score),
                        screen_score=float(screen_part_score),
                    )

                    all_candidates.append({
                        "score": score,
                        "base_cluster_idx": int(base_cluster_idx),
                        "screen_cluster_idx": int(screen_cluster_idx),
                        "axis_name": axis_c["name"],
                        "center_name": center_c["name"],
                        "angle_deg": float(angle_deg),
                        "base_part_score": float(base_part_score),
                        "screen_part_score": float(screen_part_score),
                        "physical_scores": phys,
                        "whole_symmetric_mean": whole_metrics["symmetric_mean"],
                        "bbox_volume_ratio": whole_metrics["bbox"]["bbox_volume_ratio_pred_over_gt"],
                        "collapse_flag": whole_metrics["collapse_flag"],
                        "T_base": T_base,
                        "T_screen": T_screen,
                        "base_moved": base_moved,
                        "screen_moved": screen_moved,
                        "hinge_moved": hinge_moved,
                        "union": union,
                        "whole_metrics": whole_metrics,
                    })

    all_candidates = sorted(all_candidates, key=lambda x: x["score"])
    best = all_candidates[0]

    best["base_moved"].export(out_mesh / "keyboard_base_kinematic_v1_3.ply")
    best["screen_moved"].export(out_mesh / "screen_kinematic_v1_3.ply")
    best["union"].export(out_mesh / "object_kinematic_v1_3_union.ply")
    if best["hinge_moved"] is not None:
        best["hinge_moved"].export(out_mesh / "hinge_kinematic_v1_3.ply")

    phys = best["physical_scores"]
    metrics = best["whole_metrics"]

    visual_flags = {
        "collapse_flag": bool(metrics["collapse_flag"]),
        "bbox_volume_reasonable": 0.50 <= metrics["bbox"]["bbox_volume_ratio_pred_over_gt"] <= 2.00,
        "hinge_connected": phys["hinge_gap_p5"] <= 0.020,
        "excessive_near_overlap": phys["near_fraction_5mm"] > 0.25,
        "excessive_bbox_overlap": phys["bbox_overlap_ratio"] > 0.50,
        "screen_straddles_base_plane": phys["base_plane_screen_smaller_side_ratio"] > 0.25,
    }

    if visual_flags["collapse_flag"]:
        overall = "KINEMATIC_CHAIN_V1_3_REJECTED_BY_COLLAPSE_GUARD"
    elif visual_flags["excessive_near_overlap"] or visual_flags["excessive_bbox_overlap"] or visual_flags["screen_straddles_base_plane"]:
        overall = "KINEMATIC_CHAIN_V1_3_PARTIAL_PASS_PHYSICAL_CHECK_REQUIRED"
    elif not visual_flags["hinge_connected"]:
        overall = "KINEMATIC_CHAIN_V1_3_NEEDS_HINGE_CONNECTIVITY_REFINEMENT"
    else:
        overall = "KINEMATIC_CHAIN_V1_3_NO_COLLAPSE_VISUAL_CHECK_REQUIRED"

    top = []
    for c in all_candidates[:args.top_k]:
        top.append({
            "score": c["score"],
            "base_cluster_idx": c["base_cluster_idx"],
            "screen_cluster_idx": c["screen_cluster_idx"],
            "axis_name": c["axis_name"],
            "center_name": c["center_name"],
            "angle_deg": c["angle_deg"],
            "base_part_score": c["base_part_score"],
            "screen_part_score": c["screen_part_score"],
            "physical_scores": c["physical_scores"],
            "whole_symmetric_mean": c["whole_symmetric_mean"],
            "bbox_volume_ratio": c["bbox_volume_ratio"],
            "collapse_flag": c["collapse_flag"],
        })

    result = {
        "case_id": case_root.name,
        "stage": "Gate D-0 v1.3 kinematic-chain oracle",
        "purpose": "test base-root + shared-scale + single hinge angle with physical scoring",
        "model_constraints": [
            "one shared global scale",
            "keyboard_base is root SE(3)",
            "screen has no independent translation",
            "screen rotates around one hinge axis",
            "no independent per-part scale",
            "physical scoring includes overlap/crossing proxies"
        ],
        "shared_scale": shared_scale,
        "boundary_hinge_seed": {
            "center": boundary["center"].tolist(),
            "axis": boundary["axis"].tolist(),
            "num_pairs": boundary["num_pairs"],
            "mean_pair_distance": boundary["mean_pair_distance"],
            "p95_pair_distance": boundary["p95_pair_distance"]
        },
        "search_space": {
            "num_axis_candidates": len(axis_candidates),
            "num_center_candidates": len(center_candidates),
            "num_angle_values": len(angle_values),
            "num_total_candidates": len(all_candidates),
            "angle_min": args.angle_min,
            "angle_max": args.angle_max,
            "angle_step": args.angle_step
        },
        "best": {
            "score": best["score"],
            "base_cluster_idx": best["base_cluster_idx"],
            "screen_cluster_idx": best["screen_cluster_idx"],
            "axis_name": best["axis_name"],
            "center_name": best["center_name"],
            "angle_deg": best["angle_deg"],
            "base_part_score": best["base_part_score"],
            "screen_part_score": best["screen_part_score"],
            "physical_scores": best["physical_scores"],
            "T_base": best["T_base"].tolist(),
            "T_screen": best["T_screen"].tolist()
        },
        "whole_metrics": metrics,
        "visual_flags": visual_flags,
        "top_candidates": top,
        "overall_decision": overall,
        "warnings": [
            "This is still an oracle diagnostic, not a final non-GT method.",
            "Pseudo GT screen/base split is unsupervised.",
            "Physical scoring uses proxies, not exact SDF.",
            "Visual inspection is required before Gate C v3.",
            "If this fails, move to template/CAD or silhouette-depth scoring."
        ]
    }

    out_json = out_metrics / "gate_d0_kinematic_chain_oracle_v1_3_metrics.json"
    out_json.write_text(json.dumps(result, indent=2))

    scene = trimesh.Scene()
    scene.add_geometry(v12.colorize(gt, [180, 180, 180, 80]), node_name="gt_object_gray")
    scene.add_geometry(v12.colorize(best["base_moved"], [255, 140, 0, 190]), node_name="keyboard_base_root_orange")
    scene.add_geometry(v12.colorize(best["screen_moved"], [0, 0, 255, 180]), node_name="screen_hinged_blue")
    if best["hinge_moved"] is not None:
        scene.add_geometry(v12.colorize(best["hinge_moved"], [255, 0, 255, 220]), node_name="hinge_root_magenta")
    scene.export(out_root / "visuals/gate_d0_kinematic_chain_oracle_v1_3_scene.glb")

    print("[OK] wrote", out_json)
    print("[OK] wrote", out_root / "visuals/gate_d0_kinematic_chain_oracle_v1_3_scene.glb")
    print("[DECISION]", overall)
    print("[shared_scale]", shared_scale)
    print("[best_angle_deg]", best["angle_deg"])
    print("[best_axis]", best["axis_name"])
    print("[best_center]", best["center_name"])
    print("[collapse]", metrics["collapse_flag"])
    print("[pred_to_gt_mean]", metrics["pred_to_gt"]["mean"])
    print("[gt_to_pred_mean]", metrics["gt_to_pred"]["mean"])
    print("[symmetric_mean]", metrics["symmetric_mean"])
    print("[bbox_volume_ratio]", metrics["bbox"]["bbox_volume_ratio_pred_over_gt"])
    print("[hinge_gap_p5]", phys["hinge_gap_p5"])
    print("[near_fraction_5mm]", phys["near_fraction_5mm"])
    print("[bbox_overlap_ratio]", phys["bbox_overlap_ratio"])
    print("[screen_plane_cross_ratio]", phys["base_plane_screen_smaller_side_ratio"])
    print("[searched_candidates]", len(all_candidates))


if __name__ == "__main__":
    main()
