from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contracts import file_sha256


def validate_manifest(path: Path) -> dict:
    payload=json.loads(path.read_text())
    errors=[]
    if payload.get("case_id")!="alapuse02v3n60": errors.append("case_not_allowlisted")
    if payload.get("live_authorized") is not False: errors.append("live_boundary_not_closed")
    for owner_id,item in payload.get("owners",{}).items():
        owner=Path(item["path"])
        if not owner.is_file(): errors.append(f"missing_owner:{owner_id}:{owner}")
        elif file_sha256(owner)!=item["sha256"]: errors.append(f"owner_hash_mismatch:{owner_id}")
    return {"schema":"tracehoi.AutomaticQueryValidateOnly.v1","errors":errors,
            "api_called":False,"gpu_used":False,
            "decision":"validate_only_closed" if not errors else "review_manifest_owner"}


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--validate-only",action="store_true")
    args=parser.parse_args()
    report=validate_manifest(args.manifest)
    if not args.validate_only:
        report["decision"]="hold_before_live_orchestration"
        report["errors"].append("only_validate_mode_is_authorized_in_14_112_4")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
