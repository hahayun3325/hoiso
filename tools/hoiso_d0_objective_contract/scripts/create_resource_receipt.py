#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--phase", required=True)
    ap.add_argument("--steps-requested", type=int, required=True)
    ap.add_argument("--checkpoints", default="0,1,3,5")
    ap.add_argument("--active-parameters", default="")
    ap.add_argument("--out", required=True)
    a=ap.parse_args()
    receipt={
      "schema":"hoiso_phase_resource_receipt_v1",
      "phase":a.phase,
      "steps_requested":a.steps_requested,
      "steps_completed":None,
      "checkpoints":[int(x) for x in a.checkpoints.split(",") if x.strip()],
      "active_parameters":[x.strip() for x in a.active_parameters.split(",") if x.strip()],
      "wall_seconds":None,
      "peak_cuda_allocated_mb":None,
      "peak_cuda_reserved_mb":None,
      "zero_checkpoint":None,
      "accepted_checkpoint":None,
      "decision":None,
      "notes":""
    }
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(receipt,indent=2)+"\n")
    print(f"[PASS] wrote {out}")

if __name__=="__main__": main()
