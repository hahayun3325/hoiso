from pathlib import Path
import csv

HOME = Path.home()
CASES = ["abox01", "aket01", "ascis01", "alapuse01", "amicuse01"]

def ok(p):
    return Path(p).exists() and Path(p).is_file() and Path(p).stat().st_size > 0

rows = []

for case in CASES:
    default = HOME / "foho_phase0/runs" / f"arctic_{case}_default"
    method = HOME / "foho_phase0/runs" / f"arctic_{case}_gpt55_auto_selector_native_v2"

    row = {
        "case": case,
        "default_obj": ok(default / "guidance_out" / f"{case}_obj.ply"),
        "default_hand": ok(default / "guidance_out" / f"{case}_hand.ply"),
        "method_obj": ok(method / "guidance_out" / f"{case}_obj.ply"),
        "method_hand": ok(method / "guidance_out" / f"{case}_hand.ply"),
        "default_run": str(default),
        "method_run": str(method),
    }
    row["pair_ok"] = all(row[k] for k in ["default_obj", "default_hand", "method_obj", "method_hand"])
    rows.append(row)

out = HOME / "foho_phase0/inspection/arctic_phase017/arctic_default_vs_selector_pair_verify.csv"
out.parent.mkdir(parents=True, exist_ok=True)

with open(out, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

print("[OK] wrote", out)
for r in rows:
    print(r)
