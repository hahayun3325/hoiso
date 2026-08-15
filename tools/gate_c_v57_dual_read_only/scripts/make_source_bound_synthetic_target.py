from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np

from common import ProbeConfigError, as_path, load_adapter, read_json, write_json


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--deltas-json", required=True, help="JSON object mapping manifest parameter names to source-unit deltas")
    ap.add_argument("--out", required=True)
    ap.add_argument("--metadata-out", default="")
    args = ap.parse_args()
    try:
        cfg = read_json(args.config)
        deltas = read_json(args.deltas_json)
        adapter = load_adapter(as_path(cfg, "adapter"))
        context = adapter.load_context(cfg.get("adapter_context", {}))
        zero = np.asarray(adapter.project_keypoints(context, {}), dtype=np.float64)[:, :2]
        target = np.asarray(adapter.project_keypoints(context, {str(k): float(v) for k, v in deltas.items()}), dtype=np.float64)[:, :2]
        if target.shape != zero.shape or not np.isfinite(target).all():
            raise ProbeConfigError(f"Synthetic target shape/finite check failed: {target.shape} vs {zero.shape}")
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        np.save(out, target)
        meta_path = Path(args.metadata_out) if args.metadata_out else out.with_suffix(".json")
        write_json(meta_path, {
            "status": "PASS",
            "deltas": {str(k): float(v) for k, v in deltas.items()},
            "zero_keypoints_path": str(out.with_name(out.stem + "__zero.npy")),
            "synthetic_target_path": str(out),
            "note": "Ephemeral source-bound forward evaluations only; no nonzero mesh exported."
        })
        np.save(out.with_name(out.stem + "__zero.npy"), zero)
        print(f"[OK] {out}")
        return 0
    except ProbeConfigError as exc:
        print(f"[CONFIG_ERROR] {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[ADAPTER_ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
