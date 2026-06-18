#!/usr/bin/env python
from pathlib import Path
import json

attempt = Path("/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_aket01_partaware_v2/attempt0_partaware_prompt")

required = {
    "prompt": attempt / "object_prompt_partaware_v2.txt",
    "metadata": attempt / "rerun_metadata.json",
    "state": attempt / "rerun_state.json",
    "output_contract": attempt / "output_contract.json",
    "logs": attempt / "logs",
    "run_outputs": attempt / "run_outputs",
    "selector_recheck": attempt / "selector_v4_recheck",
}

rows = []
for name, path in required.items():
    rows.append({
        "name": name,
        "path": str(path),
        "exists": path.exists(),
        "is_dir": path.is_dir(),
    })

all_ok = all(x["exists"] for x in rows)

out = attempt / "rerun_ready_check.json"
out.write_text(json.dumps({
    "case_id": "aket01",
    "attempt": 0,
    "all_ok": all_ok,
    "items": rows,
}, indent=2))

print(json.dumps({
    "case_id": "aket01",
    "attempt": 0,
    "all_ok": all_ok,
    "items": rows,
}, indent=2))
