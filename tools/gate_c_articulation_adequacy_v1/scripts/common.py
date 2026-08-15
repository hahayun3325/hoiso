from __future__ import annotations

import csv
import importlib.util
import json
import math
import os
from pathlib import Path
from typing import Any, Iterable

import numpy as np


class ProbeConfigError(RuntimeError):
    pass


def expand(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expanduser(os.path.expandvars(value))
    if isinstance(value, list):
        return [expand(v) for v in value]
    if isinstance(value, dict):
        return {k: expand(v) for k, v in value.items()}
    return value


def read_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise ProbeConfigError(f"JSON file does not exist: {p}")
    with p.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ProbeConfigError(f"Expected a JSON object: {p}")
    return expand(obj)


def write_json(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")
    tmp.replace(p)


def read_keypoints(path: str | Path) -> np.ndarray:
    p = Path(path)
    if not p.is_file():
        raise ProbeConfigError(f"Keypoint file does not exist: {p}")
    if p.suffix.lower() == ".npy":
        arr = np.load(p)
    elif p.suffix.lower() == ".npz":
        z = np.load(p)
        if "keypoints" in z:
            arr = z["keypoints"]
        elif len(z.files) == 1:
            arr = z[z.files[0]]
        else:
            raise ProbeConfigError(f"NPZ must contain 'keypoints' or one array: {p}")
    elif p.suffix.lower() == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        arr = np.asarray(data["keypoints"] if isinstance(data, dict) else data)
    else:
        raise ProbeConfigError(f"Unsupported keypoint format: {p.suffix}")
    arr = np.asarray(arr, dtype=np.float64)
    if arr.ndim == 3 and arr.shape[0] == 1:
        arr = arr[0]
    if arr.ndim != 2 or arr.shape[1] < 2:
        raise ProbeConfigError(f"Expected Nx2 or NxC keypoints, got {arr.shape} from {p}")
    arr = arr[:, :2]
    return arr


def read_confidence(path: str | Path | None, n: int) -> np.ndarray:
    if not path:
        return np.ones(n, dtype=np.float64)
    p = Path(path)
    if not p.is_file():
        raise ProbeConfigError(f"Confidence file does not exist: {p}")
    if p.suffix.lower() == ".npy":
        arr = np.load(p)
    elif p.suffix.lower() == ".npz":
        z = np.load(p)
        arr = z["confidence"] if "confidence" in z else z[z.files[0]]
    elif p.suffix.lower() == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        arr = np.asarray(data["confidence"] if isinstance(data, dict) else data)
    else:
        raise ProbeConfigError(f"Unsupported confidence format: {p.suffix}")
    arr = np.asarray(arr, dtype=np.float64).reshape(-1)
    if arr.size != n:
        raise ProbeConfigError(f"Confidence length {arr.size} != keypoint count {n}")
    if not np.isfinite(arr).all():
        raise ProbeConfigError("Confidence contains non-finite values")
    return np.clip(arr, 0.0, 1.0)


def read_manifest(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.is_file():
        raise ProbeConfigError(f"Parameter manifest does not exist: {p}")
    rows: list[dict[str, Any]] = []
    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = {"name", "group", "step", "bound", "enabled", "authorizes"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ProbeConfigError(f"Manifest is missing columns: {sorted(missing)}")
        for raw in reader:
            name = (raw.get("name") or "").strip()
            if not name or "TODO" in name.upper() or "REPLACE" in name.upper():
                raise ProbeConfigError(f"Unresolved parameter name in manifest: {name!r}")
            try:
                step = float(raw["step"])
                bound = float(raw["bound"])
            except Exception as exc:
                raise ProbeConfigError(f"Invalid step/bound for {name}: {exc}") from exc
            if not math.isfinite(step) or step <= 0:
                raise ProbeConfigError(f"Step must be positive for {name}")
            if not math.isfinite(bound) or bound <= 0:
                raise ProbeConfigError(f"Bound must be positive for {name}")
            enabled = str(raw["enabled"]).strip().lower() in {"1", "true", "yes", "y"}
            authorizes = str(raw["authorizes"]).strip().lower() in {"1", "true", "yes", "y"}
            rows.append({
                **raw,
                "name": name,
                "group": (raw.get("group") or "").strip(),
                "step": step,
                "bound": bound,
                "enabled": enabled,
                "authorizes": authorizes,
            })
    enabled_rows = [r for r in rows if r["enabled"]]
    names = [r["name"] for r in enabled_rows]
    if len(names) != len(set(names)):
        raise ProbeConfigError("Enabled parameter names are not unique")
    if not enabled_rows:
        raise ProbeConfigError("No enabled parameters in manifest")
    return rows


def load_adapter(path: str | Path):
    p = Path(path)
    if not p.is_file():
        raise ProbeConfigError(f"Adapter does not exist: {p}")
    spec = importlib.util.spec_from_file_location("gate_c_source_bound_adapter", p)
    if spec is None or spec.loader is None:
        raise ProbeConfigError(f"Cannot import adapter: {p}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for fn in ("load_context", "project_keypoints"):
        if not callable(getattr(module, fn, None)):
            raise ProbeConfigError(f"Adapter must implement {fn}(): {p}")
    return module


def ensure_keypoint_pair(a: np.ndarray, b: np.ndarray, label: str) -> None:
    if a.shape != b.shape:
        raise ProbeConfigError(f"{label}: shape mismatch {a.shape} vs {b.shape}")
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ProbeConfigError(f"{label}: non-finite keypoints")


def keypoint_metrics(pred: np.ndarray, target: np.ndarray, confidence: np.ndarray | None = None) -> dict[str, float]:
    ensure_keypoint_pair(pred, target, "keypoint_metrics")
    err = np.linalg.norm(pred - target, axis=1)
    if confidence is None:
        mask = np.ones(err.shape[0], dtype=bool)
        w = np.ones_like(err)
    else:
        confidence = np.asarray(confidence, dtype=np.float64).reshape(-1)
        mask = confidence > 0
        w = confidence
    if not np.any(mask):
        raise ProbeConfigError("No positive-confidence keypoints")
    e = err[mask]
    wm = w[mask]
    weighted_rmse = float(np.sqrt(np.sum(wm * e * e) / np.sum(wm)))
    return {
        "count": int(e.size),
        "rmse_px": float(np.sqrt(np.mean(e * e))),
        "weighted_rmse_px": weighted_rmse,
        "mean_px": float(np.mean(e)),
        "median_px": float(np.median(e)),
        "p95_px": float(np.percentile(e, 95)),
        "max_px": float(np.max(e)),
    }


def cosine(a: np.ndarray, b: np.ndarray, eps: float = 1e-12) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na <= eps and nb <= eps:
        return 1.0
    if na <= eps or nb <= eps:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def as_path(config: dict[str, Any], key: str) -> Path:
    value = config.get(key)
    if not value:
        raise ProbeConfigError(f"Missing config key: {key}")
    return Path(str(value))


def write_csv(path: str | Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
