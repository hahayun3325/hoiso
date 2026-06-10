from pathlib import Path
import csv
import re

HOME = Path.home()
CASES = ["abox01", "aket01", "ascis01", "alapuse01", "amicuse01"]

BAD_RE = re.compile(
    r"Traceback|CUDA out of memory|FileNotFoundError|RuntimeError|SyntaxError",
    re.I,
)

SELECTOR_RE = re.compile(
    r"FOHO_INTERNAL_SELECTOR|FOHO_SELECTOR_RENDER|FOHO_SELECTOR_DEBUG|gpt55_auto_selector|selector_native",
    re.I,
)

def ok(p):
    p = Path(p)
    return p.exists() and p.is_file() and p.stat().st_size > 0

rows = []

for case in CASES:
    default = HOME / "foho_phase0/runs" / f"arctic_{case}_default"
    method = HOME / "foho_phase0/runs" / f"arctic_{case}_gpt55_auto_selector_native_v2"

    clean_log = HOME / "foho_phase0/logs" / f"arctic_{case}_default.clean_default.log"
    old_log = HOME / "foho_phase0/logs" / f"arctic_{case}_default.log"
    log = clean_log if clean_log.exists() else old_log
    text = log.read_text(errors="ignore") if log.exists() else ""

    row = {
        "case": case,
        "default_obj": ok(default / "guidance_out" / f"{case}_obj.ply"),
        "default_hand": ok(default / "guidance_out" / f"{case}_hand.ply"),
        "method_obj": ok(method / "guidance_out" / f"{case}_obj.ply"),
        "method_hand": ok(method / "guidance_out" / f"{case}_hand.ply"),
        "default_log": str(log),
        "default_log_bad": bool(BAD_RE.search(text)),
        "default_log_has_selector": bool(SELECTOR_RE.search(text)),
    }
    row["pair_ok"] = all(row[k] for k in ["default_obj", "default_hand", "method_obj", "method_hand"])
    row["clean_pair_ok"] = row["pair_ok"] and not row["default_log_bad"] and not row["default_log_has_selector"]
    rows.append(row)

out = HOME / "foho_phase0/inspection/arctic_phase017/arctic_clean_default_vs_selector_pair_verify.csv"
out.parent.mkdir(parents=True, exist_ok=True)

with open(out, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

print("[OK] wrote", out)
for r in rows:
    print(r)
