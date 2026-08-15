#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--schema", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    inp, sch, out = map(Path, (args.input, args.schema, args.out))
    report = {"status": "HOLD", "input": str(inp), "schema": str(sch), "errors": []}
    try:
        data = json.loads(inp.read_text())
        schema = json.loads(sch.read_text())
    except Exception as e:
        report["errors"].append(f"read_or_json_error:{type(e).__name__}:{e}")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2)+"\n")
        print(json.dumps(report, indent=2))
        return 2
    try:
        import jsonschema
        jsonschema.validate(data, schema)
    except ImportError:
        required = schema.get("required", [])
        missing = [k for k in required if k not in data]
        if missing:
            report["errors"].append(f"missing_required:{missing}")
    except Exception as e:
        report["errors"].append(f"schema_validation:{type(e).__name__}:{e}")
    if data.get("decision") != "compile":
        report["errors"].append(f"decision_not_compile:{data.get('decision')}")
    if not data.get("contacts") and data.get("contact_state") not in {"no_contact", "uncertain"}:
        report["errors"].append("nonempty_contacts_required_for_contact_state")
    report["status"] = "PASS" if not report["errors"] else "HOLD"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
