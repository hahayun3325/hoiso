#!/usr/bin/env python3
"""Read-only v98 residual morphology audit.

This script does not run MANO, collect derivatives, change bounds, or optimize.
It analyzes the residual at a frozen nonlinear path sample (normally alpha=1)
using simple 2D diagnostic models: translation, rotation about the projected
wrist, isotropic scale about the projected wrist, and their combinations.
These are screening diagnostics only; they do not prove a 3D source family.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

JOINT_NAMES = [
    "wrist",
    "thumb_mcp", "thumb_pip", "thumb_dip", "thumb_tip",
    "index_mcp", "index_pip", "index_dip", "index_tip",
    "middle_mcp", "middle_pip", "middle_dip", "middle_tip",
    "ring_mcp", "ring_pip", "ring_dip", "ring_tip",
    "pinky_mcp", "pinky_pip", "pinky_dip", "pinky_tip",
]
CHAINS = {
    "wrist": [0],
    "thumb": [1, 2, 3, 4],
    "index": [5, 6, 7, 8],
    "middle": [9, 10, 11, 12],
    "ring": [13, 14, 15, 16],
    "pinky": [17, 18, 19, 20],
}


def load_array(path: Path) -> np.ndarray:
    if not path.is_file():
        raise FileNotFoundError(path)
    return np.asarray(np.load(path), dtype=np.float64)


def load_weights(path: Path | None, identity_confirmed: bool) -> np.ndarray:
    if path is not None and identity_confirmed:
        raise ValueError("Use either --weights or --identity-weights-confirmed, not both")
    if path is None and not identity_confirmed:
        raise ValueError("Provide source-bound --weights or --identity-weights-confirmed")
    if path is None:
        return np.ones(21, dtype=np.float64)
    raw = load_array(path).squeeze()
    if raw.shape == (21, 2):
        raw = raw.mean(axis=1)
    if raw.shape != (21,):
        raise ValueError(f"weights must have shape (21,) or (21,2), got {raw.shape}")
    if not np.all(np.isfinite(raw)) or np.any(raw < 0) or float(raw.sum()) <= 0:
        raise ValueError("weights must be finite, nonnegative, and have positive sum")
    return raw


def weighted_fit(A: np.ndarray, y: np.ndarray, coord_weights: np.ndarray) -> dict[str, Any]:
    sw = np.sqrt(coord_weights)
    Aw = A * sw[:, None]
    yw = y * sw
    beta, *_ = np.linalg.lstsq(Aw, yw, rcond=None)
    pred = A @ beta
    resid = y - pred
    sse = float(np.sum(coord_weights * resid * resid))
    total = float(np.sum(coord_weights * y * y))
    explained = 0.0 if total <= 0 else 1.0 - sse / total
    return {
        "coefficients": beta.tolist(),
        "weighted_sse": sse,
        "weighted_energy_explained": explained,
        "prediction": pred,
        "residual": resid,
    }


def design_matrices(prediction: np.ndarray) -> dict[str, np.ndarray]:
    wrist = prediction[0]
    p = prediction - wrist[None, :]
    perp = np.stack([-p[:, 1], p[:, 0]], axis=1)
    n = prediction.shape[0]
    tx = np.zeros((n, 2, 2), dtype=np.float64)
    tx[:, 0, 0] = 1.0
    tx[:, 1, 1] = 1.0
    T = tx.reshape(-1, 2)
    S = p.reshape(-1, 1)
    R = perp.reshape(-1, 1)
    return {
        "translation": T,
        "scale": S,
        "rotation": R,
        "translation_scale": np.concatenate([T, S], axis=1),
        "translation_rotation": np.concatenate([T, R], axis=1),
        "similarity": np.concatenate([T, S, R], axis=1),
    }


def route_suggestion(metrics: dict[str, float], fractions: dict[str, float], policy: dict[str, Any]) -> tuple[str, list[str]]:
    t = policy["thresholds"]
    trans = metrics["translation"]
    trrot = metrics["translation_rotation"]
    trscale = metrics["translation_scale"]
    sim = metrics["similarity"]
    rot_inc = trrot - trans
    scale_inc = trscale - trans
    margin = float(t["model_preference_margin"])
    reasons: list[str] = []

    if sim < float(t["full_similarity_explained_min"]):
        reasons.append("A 2D similarity diagnostic explains too little residual energy.")
        return "F98_C_alternate_same_run_hamer_candidate", reasons

    if (
        trans >= float(t["translation_explained_min"])
        and rot_inc < float(t["new_mode_increment_min"])
        and scale_inc < float(t["new_mode_increment_min"])
    ):
        reasons.append("A common 2D translation explains most of the residual; new rotation/scale adds little.")
        return "F98_T_translation_radius_only_expansion", reasons

    if (
        trrot >= float(t["global_model_explained_min"])
        and rot_inc >= float(t["new_mode_increment_min"])
        and trrot >= trscale + margin
        and fractions["wrist"] <= float(t["wrist_energy_fraction_max_for_root_rotation"])
    ):
        reasons.append("Translation plus wrist-centered tangential motion is the strongest simple global model.")
        return "F98_R_translation_root_rotation_active_articulation", reasons

    if (
        trscale >= float(t["global_model_explained_min"])
        and scale_inc >= float(t["new_mode_increment_min"])
        and trscale >= trrot + margin
    ):
        reasons.append("Translation plus wrist-centered radial motion is the strongest simple global model.")
        return "F98_S_translation_hand_scale_active_articulation", reasons

    if fractions["inactive_after_similarity"] >= float(t["inactive_chain_fraction_min"]):
        reasons.append("After removing the best 2D similarity component, inactive finger chains dominate residual energy.")
        return "F98_A_source_proven_broader_articulation", reasons

    reasons.append("The diagnostic is mixed or ambiguous; do not select a new pose family automatically.")
    return "PROFESSOR_REVIEW_OR_F98_C", reasons


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--nonlinear", type=Path, required=True)
    parser.add_argument("--alphas", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--identity-weights-confirmed", action="store_true")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    target = load_array(args.target).squeeze()
    nonlinear = load_array(args.nonlinear)
    alphas = load_array(args.alphas).reshape(-1)
    weights = load_weights(args.weights, args.identity_weights_confirmed)
    policy = json.loads(args.policy.read_text())

    if target.shape != (21, 2):
        raise ValueError(f"target must be (21,2), got {target.shape}")
    if nonlinear.ndim != 3 or nonlinear.shape[1:] != (21, 2):
        raise ValueError(f"nonlinear must be (N,21,2), got {nonlinear.shape}")
    if nonlinear.shape[0] != alphas.size:
        raise ValueError("nonlinear sample count must match alpha count")

    requested_alpha = float(policy.get("alpha", 1.0))
    index = int(np.argmin(np.abs(alphas - requested_alpha)))
    if abs(float(alphas[index]) - requested_alpha) > 1e-9:
        raise ValueError(f"requested alpha {requested_alpha} not found: {alphas.tolist()}")

    prediction = nonlinear[index]
    residual = target - prediction
    y = residual.reshape(-1)
    coord_weights = np.repeat(weights, 2)
    matrices = design_matrices(prediction)

    fits: dict[str, dict[str, Any]] = {}
    for name, A in matrices.items():
        fits[name] = weighted_fit(A, y, coord_weights)

    total_energy = float(np.sum(weights[:, None] * residual * residual))
    per_joint_energy = weights * np.sum(residual * residual, axis=1)
    chain_energy = {
        chain: float(per_joint_energy[idxs].sum())
        for chain, idxs in CHAINS.items()
    }
    chain_fraction = {
        chain: (energy / total_energy if total_energy > 0 else 0.0)
        for chain, energy in chain_energy.items()
    }

    sim_residual = fits["similarity"]["residual"].reshape(21, 2)
    sim_energy = weights * np.sum(sim_residual * sim_residual, axis=1)
    sim_total = float(sim_energy.sum())
    inactive_idxs = CHAINS["thumb"] + CHAINS["ring"] + CHAINS["pinky"]
    active_idxs = CHAINS["index"] + CHAINS["middle"]
    fractions = {
        "wrist": chain_fraction["wrist"],
        "active": float(per_joint_energy[active_idxs].sum() / total_energy) if total_energy > 0 else 0.0,
        "inactive": float(per_joint_energy[inactive_idxs].sum() / total_energy) if total_energy > 0 else 0.0,
        "inactive_after_similarity": float(sim_energy[inactive_idxs].sum() / sim_total) if sim_total > 0 else 0.0,
    }
    model_metrics = {
        name: float(result["weighted_energy_explained"])
        for name, result in fits.items()
    }
    suggestion, reasons = route_suggestion(model_metrics, fractions, policy)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    norms = np.linalg.norm(residual, axis=1)
    for i, name in enumerate(JOINT_NAMES):
        rows.append({
            "joint_index": i,
            "joint_name": name,
            "weight": float(weights[i]),
            "residual_x_px": float(residual[i, 0]),
            "residual_y_px": float(residual[i, 1]),
            "residual_l2_px": float(norms[i]),
            "weighted_residual_energy": float(per_joint_energy[i]),
            "similarity_residual_l2_px": float(np.linalg.norm(sim_residual[i])),
        })
    with (args.out_dir / "per_joint_residuals_v98.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    report = {
        "schema": "residual_morphology_report_v98",
        "case_id": policy.get("case_id", "alapuse02v3n60"),
        "alpha": requested_alpha,
        "input_shapes": {
            "target": list(target.shape),
            "nonlinear": list(nonlinear.shape),
            "alphas": list(alphas.shape),
        },
        "residual_metrics": {
            "coordinate_rmse_px": float(np.sqrt(np.mean(residual * residual))),
            "joint_l2_p95_px": float(np.percentile(norms, 95)),
            "maximum_joint_l2_px": float(norms.max()),
        },
        "weighted_energy_explained": model_metrics,
        "incremental_energy_explained": {
            "rotation_over_translation": model_metrics["translation_rotation"] - model_metrics["translation"],
            "scale_over_translation": model_metrics["translation_scale"] - model_metrics["translation"],
        },
        "model_coefficients": {
            name: result["coefficients"] for name, result in fits.items()
        },
        "chain_energy_fraction": chain_fraction,
        "group_energy_fraction": fractions,
        "screening_suggestion": suggestion,
        "screening_reasons": reasons,
        "limitations": [
            "This is a 2D morphology screen, not proof of a 3D root-rotation, scale, or candidate hypothesis.",
            "Any selected family still requires a source seam, zero identity, derivative stability, novelty, and bounded capacity review.",
        ],
        "authorizes_derivative_collection": False,
        "authorizes_optimizer": False,
    }
    (args.out_dir / "residual_morphology_report_v98.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    md = [
        "# v98 residual morphology screening",
        "",
        f"- Suggested route: `{suggestion}`",
        f"- Coordinate RMSE: {report['residual_metrics']['coordinate_rmse_px']:.6f} px",
        f"- Joint-L2 p95: {report['residual_metrics']['joint_l2_p95_px']:.6f} px",
        "",
        "## Weighted residual-energy explained",
        "",
    ]
    for name, value in model_metrics.items():
        md.append(f"- `{name}`: {value:.6f}")
    md += ["", "## Reasons", ""] + [f"- {reason}" for reason in reasons]
    md += [
        "",
        "## Authorization",
        "",
        "- New derivative collection: **not authorized**",
        "- Optimizer execution: **not authorized**",
        "",
    ]
    (args.out_dir / "residual_morphology_screening_v98.md").write_text("\n".join(md))
    print(f"[PASS] report={args.out_dir / 'residual_morphology_report_v98.json'}")
    print(f"[PASS] table={args.out_dir / 'per_joint_residuals_v98.csv'}")
    print(f"[INFO] suggested_route={suggestion}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
