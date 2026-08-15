from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

import numpy as np


def sha256_file(path: str | Path) -> str:
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def to_numpy(value: Any) -> np.ndarray:
    """Convert NumPy/Torch-like values to a detached CPU ndarray."""
    try:
        import torch

        if isinstance(value, torch.Tensor):
            return value.detach().cpu().numpy()
    except Exception:
        pass
    if isinstance(value, np.ndarray):
        if value.dtype == object and value.shape == ():
            return to_numpy(value.item())
        return value
    if hasattr(value, "detach") and hasattr(value, "cpu") and hasattr(value, "numpy"):
        return value.detach().cpu().numpy()
    return np.asarray(value)


def load_pickle_npy_dict(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    arr = np.load(p, allow_pickle=True)
    if isinstance(arr, np.ndarray) and arr.shape == ():
        obj = arr.item()
    else:
        obj = arr
    if not isinstance(obj, dict):
        raise TypeError(f"Expected a dict in {p}, got {type(obj).__name__}")
    return obj


def squeeze_points(array: Any, dims: int | None = None) -> np.ndarray:
    x = np.asarray(to_numpy(array), dtype=np.float64)
    while x.ndim > 2 and x.shape[0] == 1:
        x = x[0]
    if x.ndim != 2:
        raise ValueError(f"Expected point array with 2 dimensions after squeeze, got {x.shape}")
    if dims is not None and x.shape[1] != dims:
        raise ValueError(f"Expected {dims} coordinates per point, got {x.shape}")
    if not np.isfinite(x).all():
        raise ValueError("Point array contains non-finite values")
    return x


def select_candidate(array: Any, candidate_index: int, final_dims: int = 3) -> np.ndarray:
    x = np.asarray(to_numpy(array))
    if x.ndim == 2 and x.shape[-1] == final_dims:
        if candidate_index != 0:
            raise IndexError(f"Array has no candidate axis; candidate_index must be 0, got {candidate_index}")
        return x.astype(np.float64)
    if x.ndim >= 3 and x.shape[-1] == final_dims:
        if candidate_index < 0 or candidate_index >= x.shape[0]:
            raise IndexError(f"candidate_index {candidate_index} outside [0,{x.shape[0]-1}]")
        out = x[candidate_index]
        while out.ndim > 2 and out.shape[0] == 1:
            out = out[0]
        if out.ndim != 2:
            raise ValueError(f"Candidate point array has unexpected shape {out.shape}")
        return out.astype(np.float64)
    raise ValueError(f"Unsupported candidate point shape: {x.shape}")


def point_metrics(a: np.ndarray, b: np.ndarray) -> Dict[str, Any]:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if a.shape != b.shape:
        return {"shape_match": False, "shape_a": list(a.shape), "shape_b": list(b.shape)}
    delta = a - b
    per_point = np.linalg.norm(delta, axis=1)
    abs_delta = np.abs(delta)
    return {
        "shape_match": True,
        "n_points": int(a.shape[0]),
        "dims": int(a.shape[1]),
        "rmse": float(np.sqrt(np.mean(delta * delta))),
        "point_rmse": float(np.sqrt(np.mean(per_point * per_point))),
        "mean_point_error": float(per_point.mean()),
        "median_point_error": float(np.median(per_point)),
        "p95_point_error": float(np.percentile(per_point, 95)),
        "max_point_error": float(per_point.max()),
        "max_abs_coordinate_error": float(abs_delta.max()),
        "per_point_error": per_point.tolist(),
    }


def pairwise_distance_matrix(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    diff = x[:, None, :] - x[None, :, :]
    return np.linalg.norm(diff, axis=-1)


def shape_metrics(a: np.ndarray, b: np.ndarray) -> Dict[str, Any]:
    if a.shape != b.shape:
        return {"shape_match": False, "shape_a": list(a.shape), "shape_b": list(b.shape)}
    ac = a - a[0:1]
    bc = b - b[0:1]
    centered = point_metrics(ac, bc)
    da = pairwise_distance_matrix(a)
    db = pairwise_distance_matrix(b)
    tri = np.triu_indices(a.shape[0], k=1)
    va = da[tri]
    vb = db[tri]
    scale_a = float(np.median(va[va > 0])) if np.any(va > 0) else 1.0
    scale_b = float(np.median(vb[vb > 0])) if np.any(vb > 0) else 1.0
    na = va / max(scale_a, 1e-12)
    nb = vb / max(scale_b, 1e-12)
    pd = na - nb
    return {
        "shape_match": True,
        "wrist_centered": centered,
        "pairwise_normalized_rmse": float(np.sqrt(np.mean(pd * pd))),
        "pairwise_normalized_p95": float(np.percentile(np.abs(pd), 95)),
        "pairwise_scale_a": scale_a,
        "pairwise_scale_b": scale_b,
    }


def reflection_x(x: np.ndarray) -> np.ndarray:
    y = np.asarray(x, dtype=np.float64).copy()
    y[:, 0] *= -1.0
    return y


def read_json(path: str | Path) -> Dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str | Path, value: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write("\n")


def load_thresholds(path: Optional[str | Path]) -> Dict[str, float]:
    defaults = {
        "h0_max_abs_m": 1e-5,
        "h0_rmse_m": 2e-6,
        "h1_max_abs_m": 1e-5,
        "h1_rmse_m": 2e-6,
        "h2_max_abs_px": 0.05,
        "h2_rmse_px": 0.01,
        "h3_max_abs_m": 1e-5,
        "h3_rmse_m": 2e-6,
        "h4_max_abs_m": 1e-5,
        "h4_rmse_m": 2e-6,
    }
    if path:
        supplied = read_json(path)
        defaults.update({k: float(v) for k, v in supplied.items() if isinstance(v, (int, float))})
    return defaults


def passes_identity(metrics: Dict[str, Any], max_abs: float, rmse: float) -> bool:
    return bool(
        metrics.get("shape_match")
        and metrics.get("max_abs_coordinate_error", math.inf) <= max_abs
        and metrics.get("rmse", math.inf) <= rmse
    )


def load_array(path: str | Path, key: Optional[str] = None, candidate_index: int = 0) -> np.ndarray:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".npy":
        value = np.load(p, allow_pickle=True)
        if isinstance(value, np.ndarray) and value.shape == () and value.dtype == object:
            value = value.item()
            if isinstance(value, dict):
                if not key:
                    raise KeyError(f"{p} stores a dict; specify --key")
                value = value[key]
    elif suffix == ".npz":
        npz = np.load(p, allow_pickle=True)
        if not key:
            if len(npz.files) != 1:
                raise KeyError(f"{p} contains keys {npz.files}; specify --key")
            key = npz.files[0]
        value = npz[key]
    elif suffix == ".json":
        data = read_json(p)
        if key:
            for part in key.split("."):
                data = data[part]
        value = data
    else:
        raise ValueError(f"Unsupported array file type: {p.suffix}")
    x = np.asarray(to_numpy(value))
    if x.ndim >= 3:
        x = x[candidate_index]
    while x.ndim > 2 and x.shape[0] == 1:
        x = x[0]
    if x.ndim != 2 or x.shape[-1] not in (2, 3):
        raise ValueError(f"Expected Nx2 or Nx3 array, got {x.shape}")
    return x.astype(np.float64)
