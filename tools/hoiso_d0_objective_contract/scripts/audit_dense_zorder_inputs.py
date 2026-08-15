#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--object-depth", required=True)
    ap.add_argument("--valid-mask", required=True)
    ap.add_argument("--hand-depth")
    ap.add_argument("--minimum-valid-pixels", type=int, default=64)
    ap.add_argument("--out", required=True)
    a=ap.parse_args()
    od=np.load(a.object_depth)
    vm=np.load(a.valid_mask).astype(bool)
    hd=np.load(a.hand_depth) if a.hand_depth else None
    errors=[]
    if od.shape!=vm.shape: errors.append(f"shape_mismatch:object={od.shape}:mask={vm.shape}")
    if hd is not None and hd.shape!=od.shape: errors.append(f"shape_mismatch:hand={hd.shape}:object={od.shape}")
    count=int(vm.sum()) if vm.shape==od.shape else 0
    if count<a.minimum_valid_pixels: errors.append(f"insufficient_valid_pixels:{count}")
    if count:
        vals=od[vm]
        if not np.isfinite(vals).all(): errors.append("nonfinite_object_depth_inside_valid_mask")
        if np.max(np.abs(vals))>1e4: errors.append("sentinel_like_object_depth_inside_valid_mask")
        if hd is not None and not np.isfinite(hd[vm]).all(): errors.append("nonfinite_hand_depth_inside_valid_mask")
    report={
      "status":"PASS" if not errors else "HOLD",
      "object_depth_shape":list(od.shape),
      "valid_pixels":count,
      "valid_fraction":float(count/od.size) if od.size else 0.0,
      "object_depth_min":float(np.min(od[vm])) if count else None,
      "object_depth_max":float(np.max(od[vm])) if count else None,
      "errors":errors,
      "authorizes_z_order_loss": not errors
    }
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    return 0 if not errors else 2

if __name__=="__main__": raise SystemExit(main())
