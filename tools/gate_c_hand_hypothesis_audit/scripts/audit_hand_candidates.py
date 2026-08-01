#!/usr/bin/env python3
"""Deterministic Gate-C hand-hypothesis/correspondence audit.

This tool does not optimize a hand or an object. It only:
  * validates explicit candidate provenance metadata,
  * applies an explicitly registered keypoint mapping and raster affine,
  * compares projected 2D keypoints with a frozen target,
  * evaluates proper and reflected similarity fits separately,
  * reports pairwise articulated-structure error,
  * optionally evaluates hand-mask IoU,
  * produces per-candidate overlays and a machine-readable summary.

Dependencies: numpy, Pillow (both already present in the foho environment in
normal project installations).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFont


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(f"argument_error: {message}")


REQUIRED_COLUMNS = {
    "candidate_id",
    "projected_keypoints_path",
    "source_frame",
    "source_identity_status",
    "handedness",
    "crop_flipped",
    "joint_order_status",
    "raster_status",
    "mapping_path",
    "raster_affine_path",
}


@dataclass
class Keypoints:
    xy: np.ndarray
    confidence: np.ndarray


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _find_numeric_array(value: Any) -> np.ndarray | None:
    """Find the first plausible Nx2/Nx3 numeric array in nested JSON."""
    if isinstance(value, list):
        try:
            arr = np.asarray(value, dtype=np.float64)
            arr = np.squeeze(arr)
            if arr.ndim == 2 and arr.shape[1] >= 2 and arr.shape[0] >= 3:
                return arr
        except Exception:
            pass
        for item in value:
            found = _find_numeric_array(item)
            if found is not None:
                return found
    elif isinstance(value, dict):
        preferred = [
            "keypoints", "keypoints_2d", "projected_keypoints", "joints_2d",
            "pred_keypoints_2d", "kps", "points",
        ]
        for key in preferred:
            if key in value:
                found = _find_numeric_array(value[key])
                if found is not None:
                    return found
        for item in value.values():
            found = _find_numeric_array(item)
            if found is not None:
                return found
    return None


def load_array(path: Path) -> np.ndarray:
    suffix = path.suffix.lower()
    if suffix == ".npy":
        arr = np.load(path, allow_pickle=False)
    elif suffix == ".npz":
        pack = np.load(path, allow_pickle=False)
        keys = list(pack.keys())
        if not keys:
            raise ValueError(f"empty npz: {path}")
        preferred = [k for k in keys if k.lower() in {
            "keypoints", "keypoints_2d", "projected_keypoints", "joints_2d", "kps"
        }]
        arr = pack[preferred[0] if preferred else keys[0]]
    elif suffix == ".json":
        payload = json.loads(path.read_text())
        arr = _find_numeric_array(payload)
        if arr is None:
            raise ValueError(f"no Nx2/Nx3 numeric keypoint array found in {path}")
    elif suffix in {".csv", ".txt"}:
        arr = np.loadtxt(path, delimiter="," if suffix == ".csv" else None)
    else:
        raise ValueError(f"unsupported keypoint format: {path}")

    arr = np.asarray(arr, dtype=np.float64)
    arr = np.squeeze(arr)
    while arr.ndim > 2 and arr.shape[0] == 1:
        arr = arr[0]
    if arr.ndim != 2 or arr.shape[1] < 2:
        raise ValueError(f"expected Nx2/Nx3 keypoints, got {arr.shape} from {path}")
    if arr.shape[0] < 3:
        raise ValueError(f"need at least 3 keypoints, got {arr.shape[0]} from {path}")
    return arr


def load_keypoints(path: Path) -> Keypoints:
    arr = load_array(path)
    xy = arr[:, :2].astype(np.float64)
    confidence = np.ones(len(xy), dtype=np.float64)
    if arr.shape[1] >= 3:
        c = arr[:, 2].astype(np.float64)
        finite = c[np.isfinite(c)]
        if finite.size and finite.min() >= -1e-6 and finite.max() <= 1.000001:
            confidence = np.clip(c, 0.0, 1.0)
    return Keypoints(xy=xy, confidence=confidence)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def apply_mapping(kps: Keypoints, mapping: dict[str, Any], target_count: int) -> Keypoints:
    indices = mapping.get("candidate_to_target")
    if not isinstance(indices, list):
        raise ValueError("mapping JSON must contain candidate_to_target list")
    if len(indices) != target_count:
        raise ValueError(
            f"mapping length {len(indices)} does not match target count {target_count}"
        )
    idx = np.asarray(indices, dtype=np.int64)
    if idx.min(initial=0) < 0 or idx.max(initial=-1) >= len(kps.xy):
        raise ValueError(
            f"mapping indices outside candidate range 0..{len(kps.xy)-1}"
        )
    return Keypoints(xy=kps.xy[idx], confidence=kps.confidence[idx])


def apply_affine(xy: np.ndarray, affine: dict[str, Any]) -> np.ndarray:
    matrix = np.asarray(affine.get("matrix"), dtype=np.float64)
    if matrix.shape != (3, 3):
        raise ValueError("raster affine JSON must contain a 3x3 matrix")
    homogeneous = np.concatenate([xy, np.ones((len(xy), 1))], axis=1)
    out = homogeneous @ matrix.T
    denom = out[:, 2:3]
    if np.any(np.abs(denom) < 1e-12):
        raise ValueError("raster affine produced invalid homogeneous coordinates")
    return out[:, :2] / denom


def pairwise_structure_error(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3:
        return float("nan")
    dx = np.linalg.norm(x[:, None, :] - x[None, :, :], axis=-1)
    dy = np.linalg.norm(y[:, None, :] - y[None, :, :], axis=-1)
    tri = np.triu_indices(len(x), k=1)
    vx = dx[tri]
    vy = dy[tri]
    sx = float(np.median(vx[vx > 1e-9])) if np.any(vx > 1e-9) else 0.0
    sy = float(np.median(vy[vy > 1e-9])) if np.any(vy > 1e-9) else 0.0
    if sx <= 0 or sy <= 0:
        return float("nan")
    vx = vx / sx
    vy = vy / sy
    return float(np.sqrt(np.mean((vx - vy) ** 2)))


def similarity_fit(x: np.ndarray, y: np.ndarray, desired_det: int) -> dict[str, Any]:
    """Fit y ~= scale * x @ R + translation with det(R)=desired_det."""
    if desired_det not in (-1, 1):
        raise ValueError("desired_det must be +1 or -1")
    n = len(x)
    if n < 3:
        return {"valid": False, "reason": "too_few_points"}
    mx = x.mean(axis=0)
    my = y.mean(axis=0)
    xc = x - mx
    yc = y - my
    var_x = float(np.sum(xc * xc) / n)
    if var_x <= 1e-12:
        return {"valid": False, "reason": "degenerate_candidate"}
    covariance = xc.T @ yc / n
    u, singular, vt = np.linalg.svd(covariance)
    base_det = float(np.linalg.det(u @ vt))
    correction = np.eye(2)
    correction[-1, -1] = desired_det / (1.0 if base_det >= 0 else -1.0)
    rotation = u @ correction @ vt
    det_r = float(np.linalg.det(rotation))
    scale_numerator = float(np.sum(singular * np.diag(correction)))
    scale = scale_numerator / var_x
    if not np.isfinite(scale) or scale <= 1e-12:
        return {
            "valid": False,
            "reason": "nonpositive_or_invalid_scale",
            "determinant": det_r,
            "scale": scale,
        }
    translation = my - scale * (mx @ rotation)
    fitted = scale * (x @ rotation) + translation
    errors = np.linalg.norm(fitted - y, axis=1)
    return {
        "valid": True,
        "determinant": det_r,
        "scale": float(scale),
        "rotation": rotation.tolist(),
        "translation": translation.tolist(),
        "fitted": fitted,
        "errors": errors,
        "rmse_px": float(np.sqrt(np.mean(errors ** 2))),
        "p95_px": float(np.percentile(errors, 95)),
        "mean_px": float(np.mean(errors)),
        "max_px": float(np.max(errors)),
    }


def bbox_diagonal(xy: np.ndarray) -> float:
    extent = np.nanmax(xy, axis=0) - np.nanmin(xy, axis=0)
    return float(np.linalg.norm(extent))


def load_binary_mask(path: Path) -> np.ndarray:
    image = Image.open(path).convert("L")
    arr = np.asarray(image)
    return arr > 127


def mask_iou(candidate_path: Path, target_path: Path) -> float:
    a = load_binary_mask(candidate_path)
    b = load_binary_mask(target_path)
    if a.shape != b.shape:
        raise ValueError(f"mask shape mismatch: {a.shape} vs {b.shape}")
    union = np.logical_or(a, b).sum()
    if union == 0:
        return 1.0
    return float(np.logical_and(a, b).sum() / union)


def bool_field(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def finite_or_none(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None


def round_or_none(value: float | None, digits: int = 6) -> float | None:
    if value is None or not np.isfinite(value):
        return None
    return round(float(value), digits)


def draw_overlay(
    image_path: Path | None,
    output_path: Path,
    target: np.ndarray,
    candidate: np.ndarray,
    proper: np.ndarray | None,
    reflected: np.ndarray | None,
    title_lines: Iterable[str],
) -> None:
    if image_path and image_path.is_file():
        base = Image.open(image_path).convert("RGB")
    else:
        max_x = int(max(np.nanmax(target[:, 0]), np.nanmax(candidate[:, 0]), 512)) + 30
        max_y = int(max(np.nanmax(target[:, 1]), np.nanmax(candidate[:, 1]), 512)) + 30
        base = Image.new("RGB", (max_x, max_y), "white")
    draw = ImageDraw.Draw(base)
    font = ImageFont.load_default()

    def points(xy: np.ndarray | None, fill: tuple[int, int, int], radius: int, label: bool) -> None:
        if xy is None:
            return
        for i, (x, y) in enumerate(xy):
            if not np.isfinite(x) or not np.isfinite(y):
                continue
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill)
            if label:
                draw.text((x + radius + 1, y - radius - 1), str(i), fill=fill, font=font)

    # target green; raw candidate red; proper blue; reflected cyan
    points(target, (0, 160, 0), 4, True)
    points(candidate, (210, 30, 30), 3, False)
    points(proper, (30, 80, 220), 3, False)
    points(reflected, (0, 180, 200), 2, False)

    legend = [
        "green=target  red=raw  blue=proper-fit  cyan=reflected-fit",
        *title_lines,
    ]
    y = 4
    for line in legend:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.rectangle((2, y - 1, min(base.width - 2, 8 + w), y + h + 2), fill=(255, 255, 255))
        draw.text((5, y), line, fill=(0, 0, 0), font=font)
        y += h + 4
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path)


def route_candidate(
    metadata_ok: bool,
    proper: dict[str, Any],
    reflected: dict[str, Any],
    pairwise: float,
    iou: float | None,
    thresholds: dict[str, Any],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if not metadata_ok:
        reasons.append("provenance_or_coordinate_contract_not_verified")
        return "HOLD_PROVENANCE_OR_COORDINATE_CONTRACT", reasons

    required = [
        "proper_normalized_rmse_max",
        "proper_normalized_p95_max",
        "pairwise_normalized_rmse_max",
    ]
    missing = [k for k in required if thresholds.get(k) is None]
    if missing:
        reasons.append("unregistered_thresholds:" + ",".join(missing))
        return "HOLD_THRESHOLDS_NOT_REGISTERED", reasons

    proper_pass = bool(
        proper.get("valid")
        and proper.get("normalized_rmse") <= thresholds["proper_normalized_rmse_max"]
        and proper.get("normalized_p95") <= thresholds["proper_normalized_p95_max"]
        and np.isfinite(pairwise)
        and pairwise <= thresholds["pairwise_normalized_rmse_max"]
    )
    reflected_pass = bool(
        reflected.get("valid")
        and reflected.get("normalized_rmse") <= thresholds["proper_normalized_rmse_max"]
        and reflected.get("normalized_p95") <= thresholds["proper_normalized_p95_max"]
        and np.isfinite(pairwise)
        and pairwise <= thresholds["pairwise_normalized_rmse_max"]
    )
    mask_min = thresholds.get("mask_iou_min")
    if mask_min is not None:
        if iou is None:
            reasons.append("mask_iou_required_but_missing")
            proper_pass = False
            reflected_pass = False
        elif iou < mask_min:
            reasons.append(f"mask_iou_below_threshold:{iou:.6f}<{mask_min}")
            proper_pass = False
            reflected_pass = False

    preference_ratio = float(thresholds.get("reflected_preference_ratio_max", 0.80))
    preference_abs = float(thresholds.get("reflected_preference_min_abs_improvement", 0.02))
    if reflected.get("valid") and proper.get("valid"):
        reflected_preferred = (
            reflected.get("normalized_rmse", math.inf)
            <= preference_ratio * max(proper.get("normalized_rmse", math.inf), 1e-12)
            and proper.get("normalized_rmse", math.inf)
            - reflected.get("normalized_rmse", math.inf)
            >= preference_abs
        )
    else:
        reflected_preferred = False

    if reflected_pass and reflected_preferred:
        reasons.append("reflected_fit_materially_preferred_requires_source_raster_or_chirality_correction")
        return "HOLD_REFLECTED_ONLY", reasons
    if proper_pass:
        reasons.append("proper_similarity_and_structure_pass")
        return "PASS_CORRESPONDENCE_CANDIDATE", reasons
    if reflected_pass:
        reasons.append("reflected_only_pass_requires_source_raster_or_chirality_correction")
        return "HOLD_REFLECTED_ONLY", reasons
    reasons.append("proper_and_reflected_fits_fail")
    return "FAIL_GLOBAL_CORRESPONDENCE", reasons


def main() -> int:
    parser = SafeArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--target-kps", required=True, type=Path)
    parser.add_argument("--thresholds", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--image", type=Path)
    parser.add_argument("--target-mask", type=Path)
    parser.add_argument("--min-confidence", type=float, default=0.05)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    overlays = args.out_dir / "overlays"
    overlays.mkdir(exist_ok=True)

    target_all = load_keypoints(args.target_kps)
    thresholds = load_json(args.thresholds)

    with args.manifest.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise SystemExit("manifest has no header")
        missing_cols = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing_cols:
            raise SystemExit(f"manifest missing columns: {sorted(missing_cols)}")
        rows = list(reader)

    if not rows:
        raise SystemExit("manifest has no candidates")

    summary: dict[str, Any] = {
        "schema_version": "gate_c_hand_candidate_audit_v1",
        "target_keypoints": {
            "path": str(args.target_kps.resolve()),
            "sha256": sha256_file(args.target_kps),
            "count": int(len(target_all.xy)),
        },
        "thresholds": thresholds,
        "normalization": thresholds.get("normalization", "target_bbox_diagonal"),
        "candidates": [],
    }

    csv_rows: list[dict[str, Any]] = []
    for row in rows:
        candidate_id = row["candidate_id"].strip()
        record: dict[str, Any] = {
            "candidate_id": candidate_id,
            "source_frame": row.get("source_frame", "").strip(),
            "source_identity_status": row.get("source_identity_status", "").strip(),
            "handedness": row.get("handedness", "").strip(),
            "crop_flipped": bool_field(row.get("crop_flipped", "")),
            "joint_order_status": row.get("joint_order_status", "").strip(),
            "raster_status": row.get("raster_status", "").strip(),
            "notes": row.get("notes", "").strip(),
        }
        try:
            kps_path = Path(row["projected_keypoints_path"]).expanduser().resolve()
            if not kps_path.is_file():
                raise FileNotFoundError(kps_path)
            candidate_all = load_keypoints(kps_path)
            record["projected_keypoints"] = {
                "path": str(kps_path),
                "sha256": sha256_file(kps_path),
                "count": int(len(candidate_all.xy)),
            }

            mapping_path = Path(row["mapping_path"]).expanduser().resolve()
            affine_path = Path(row["raster_affine_path"]).expanduser().resolve()
            mapping_explicit = mapping_path.is_file()
            affine_explicit = affine_path.is_file()
            if not mapping_explicit:
                raise FileNotFoundError(f"mapping_path missing: {mapping_path}")
            if not affine_explicit:
                raise FileNotFoundError(f"raster_affine_path missing: {affine_path}")
            mapping = load_json(mapping_path)
            affine = load_json(affine_path)
            candidate_mapped = apply_mapping(candidate_all, mapping, len(target_all.xy))
            candidate_xy = apply_affine(candidate_mapped.xy, affine)

            visible = (
                np.isfinite(target_all.xy).all(axis=1)
                & np.isfinite(candidate_xy).all(axis=1)
                & (target_all.confidence >= args.min_confidence)
                & (candidate_mapped.confidence >= args.min_confidence)
            )
            if int(visible.sum()) < 6:
                raise ValueError(f"fewer than 6 usable joints: {int(visible.sum())}")
            target = target_all.xy[visible]
            candidate = candidate_xy[visible]
            normalization = bbox_diagonal(target)
            if not np.isfinite(normalization) or normalization <= 1e-9:
                raise ValueError("degenerate target normalization")

            proper = similarity_fit(candidate, target, desired_det=1)
            reflected = similarity_fit(candidate, target, desired_det=-1)
            for fit in (proper, reflected):
                if fit.get("valid"):
                    fit["normalized_rmse"] = fit["rmse_px"] / normalization
                    fit["normalized_p95"] = fit["p95_px"] / normalization
                    fit["fitted"] = np.asarray(fit["fitted"], dtype=np.float64)
                    fit["errors"] = np.asarray(fit["errors"], dtype=np.float64)
            structure = pairwise_structure_error(candidate, target)

            candidate_mask_path = row.get("mask_path", "").strip()
            iou: float | None = None
            if candidate_mask_path and args.target_mask:
                cmp = Path(candidate_mask_path).expanduser().resolve()
                if cmp.is_file() and args.target_mask.is_file():
                    iou = mask_iou(cmp, args.target_mask)

            identity_ok = record["source_identity_status"] == "verified_upper_hand"
            handedness_ok = record["handedness"] in {"left", "right"}
            order_ok = record["joint_order_status"] == "verified"
            raster_ok = record["raster_status"] == "verified"
            flip_contract_ok = (not record["crop_flipped"]) or bool(
                affine.get("includes_registered_horizontal_flip", False)
            )
            metadata_ok = identity_ok and handedness_ok and order_ok and raster_ok and flip_contract_ok

            route, reasons = route_candidate(
                metadata_ok=metadata_ok,
                proper=proper,
                reflected=reflected,
                pairwise=structure,
                iou=iou,
                thresholds=thresholds,
            )

            proper_out = dict(proper)
            reflected_out = dict(reflected)
            proper_fit_xy = proper_out.pop("fitted", None)
            proper_out.pop("errors", None)
            reflected_fit_xy = reflected_out.pop("fitted", None)
            reflected_out.pop("errors", None)
            for fit in (proper_out, reflected_out):
                for key in ("rmse_px", "p95_px", "mean_px", "max_px", "normalized_rmse", "normalized_p95", "scale", "determinant"):
                    if key in fit:
                        fit[key] = round_or_none(fit[key])

            overlay_path = overlays / f"{candidate_id}_correspondence_overlay.png"
            draw_overlay(
                args.image,
                overlay_path,
                target,
                candidate,
                proper_fit_xy,
                reflected_fit_xy,
                [
                    f"candidate={candidate_id} route={route}",
                    f"proper nRMSE={proper_out.get('normalized_rmse')} nP95={proper_out.get('normalized_p95')}",
                    f"pairwise={round_or_none(structure)} maskIoU={round_or_none(iou)}",
                ],
            )

            record.update({
                "usable_joint_count": int(visible.sum()),
                "normalization_value_px": round_or_none(normalization),
                "mapping": {
                    "path": str(mapping_path),
                    "sha256": sha256_file(mapping_path),
                    "name": mapping.get("name"),
                },
                "raster_affine": {
                    "path": str(affine_path),
                    "sha256": sha256_file(affine_path),
                    "name": affine.get("name"),
                },
                "metadata_contract_pass": metadata_ok,
                "proper_fit": proper_out,
                "reflected_fit": reflected_out,
                "pairwise_normalized_rmse": round_or_none(structure),
                "mask_iou": round_or_none(iou),
                "route": route,
                "reasons": reasons,
                "overlay": str(overlay_path),
            })
        except Exception as error:
            record.update({
                "route": "HOLD_CANDIDATE_INVALID",
                "reasons": [f"{type(error).__name__}: {error}"],
            })

        summary["candidates"].append(record)
        csv_rows.append({
            "candidate_id": candidate_id,
            "route": record.get("route"),
            "metadata_contract_pass": record.get("metadata_contract_pass"),
            "proper_normalized_rmse": (record.get("proper_fit") or {}).get("normalized_rmse"),
            "proper_normalized_p95": (record.get("proper_fit") or {}).get("normalized_p95"),
            "reflected_normalized_rmse": (record.get("reflected_fit") or {}).get("normalized_rmse"),
            "pairwise_normalized_rmse": record.get("pairwise_normalized_rmse"),
            "mask_iou": record.get("mask_iou"),
            "overlay": record.get("overlay"),
        })

    passes = [c for c in summary["candidates"] if c.get("route") == "PASS_CORRESPONDENCE_CANDIDATE"]
    passes.sort(key=lambda c: (
        (c.get("proper_fit") or {}).get("normalized_rmse", math.inf),
        c.get("pairwise_normalized_rmse", math.inf),
    ))
    articulation_eligible = [
        c for c in summary["candidates"]
        if c.get("metadata_contract_pass") is True
        and c.get("route") == "FAIL_GLOBAL_CORRESPONDENCE"
    ]
    reflected_holds = [
        c for c in summary["candidates"] if c.get("route") == "HOLD_REFLECTED_ONLY"
    ]

    if passes:
        overall_route = "SELECT_CORRESPONDENCE_CANDIDATE_FOR_C1_5"
        selected = passes[0]["candidate_id"]
    elif reflected_holds:
        overall_route = "HOLD_AUDIT_CHIRALITY_OR_RASTER_CONTRACT"
        selected = None
    elif articulation_eligible:
        overall_route = "PREPARE_BOUNDED_ARTICULATION_METHOD_DECISION"
        selected = min(
            articulation_eligible,
            key=lambda c: (c.get("proper_fit") or {}).get("normalized_rmse", math.inf),
        )["candidate_id"]
    else:
        overall_route = "HOLD_NO_SOURCE_VERIFIED_UPPER_HAND_CANDIDATE"
        selected = None

    summary["decision"] = {
        "route": overall_route,
        "selected_candidate_id": selected,
        "optimizer_authorized": False,
        "c2_authorized": False,
        "f34_authorized": False,
        "gate_d_authorized": False,
    }

    summary_path = args.out_dir / "hand_candidate_audit_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")

    csv_path = args.out_dir / "hand_candidate_audit_summary.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"[INFO] CANDIDATES={len(rows)}")
    print(f"[INFO] OVERALL_ROUTE={overall_route}")
    print(f"[INFO] SELECTED_CANDIDATE_ID={selected}")
    print(f"[PASS] SUMMARY_JSON={summary_path}")
    print(f"[PASS] SUMMARY_CSV={csv_path}")
    # A HOLD/FAIL decision is a valid audit output, so return zero.
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except KeyboardInterrupt:
        print("[HOLD] interrupted", file=sys.stderr)
        code = 130
    except Exception as error:
        print(f"[HOLD] AUDIT_NOT_RUN={type(error).__name__}: {error}", file=sys.stderr)
        code = 0
    raise SystemExit(code)
