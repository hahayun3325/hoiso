#!/usr/bin/env python
from pathlib import Path
import re
import pandas as pd

ROOT = Path("/home/fredcui/Projects/FollowMyHold")
PIPE_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline")
MANIFEST = PIPE_OUT / "selector_v41_full_pipeline_manifest.csv"
OUT = PIPE_OUT / "selector_v41_full_pipeline_preflight.csv"

def read_env_value(cfg_path: Path, key: str):
    text = cfg_path.read_text()
    m = re.search(rf'^{key}="([^"]*)"', text, flags=re.MULTILINE)
    return m.group(1) if m else ""

df = pd.read_csv(MANIFEST)
rows = []
ok = True

for _, r in df.iterrows():
    case = r["case"]
    run_id = r["new_run_id"]
    cfg = ROOT / "configs/generated" / f"pipeline.phase1.{run_id}.env"

    gemini = Path(read_env_value(cfg, "GEMINI_RESPONSES"))
    output_dir = Path(read_env_value(cfg, "OUTPUT_DIR"))
    foho_run_dir = Path(read_env_value(cfg, "FOHO_RUN_DIR"))
    env_run_id = read_env_value(cfg, "RUN_ID")

    row_ok = (
        cfg.exists()
        and gemini.exists()
        and output_dir.exists()
        and foho_run_dir.exists()
        and env_run_id == run_id
        and "selector_v41_full_pipeline" in str(output_dir)
    )

    ok = ok and row_ok

    rows.append({
        "case": case,
        "expected_run_id": run_id,
        "env_run_id": env_run_id,
        "cfg": str(cfg),
        "cfg_exists": cfg.exists(),
        "gemini_responses": str(gemini),
        "gemini_exists": gemini.exists(),
        "output_dir": str(output_dir),
        "output_dir_exists": output_dir.exists(),
        "foho_run_dir": str(foho_run_dir),
        "foho_run_dir_exists": foho_run_dir.exists(),
        "preflight_ok": row_ok,
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

print("[OK] wrote", OUT)
print(out.to_string(index=False))
print("all_preflight_ok =", ok)

if not ok:
    raise SystemExit("[BAD] preflight failed")
