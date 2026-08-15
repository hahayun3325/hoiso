#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

EXPECTED = "pass_shared_zero_adapter_prepare_read_only_articulation_probe_v56"

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--route", required=True)
    p.add_argument("--out", required=False)
    args = p.parse_args()
    path = Path(args.route)
    result = {"schema": "v56_route_validation_v1", "route_path": str(path), "expected": EXPECTED}
    if not path.is_file():
        result.update(status="HOLD", reason="route_missing")
    else:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            decision = data.get("decision")
            result.update(
                decision=decision,
                next_authorized_action=data.get("next_authorized_action"),
                authorizes_nonzero_adapter_state=data.get("authorizes_nonzero_adapter_state"),
                authorizes_placement_optimizer=data.get("authorizes_placement_optimizer"),
                authorizes_C2_F34_or_GateD=data.get("authorizes_C2_F34_or_GateD"),
            )
            result["status"] = "PASS" if decision == EXPECTED else "HOLD"
            if result["status"] != "PASS":
                result["reason"] = "unexpected_decision"
        except Exception as exc:
            result.update(status="HOLD", reason=f"parse_error:{type(exc).__name__}:{exc}")
    if args.out:
        out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
