from pathlib import Path
import re
import csv

HOME = Path.home()

runs = [
    "arctic_abox01_gpt55_auto",
    "arctic_aket01_gpt55_auto",
    "arctic_ascis01_gpt55_auto",
    "arctic_alapuse01_gpt55_auto",
    "arctic_amicuse01_gpt55_auto",
]

out_dir = HOME / "foho_phase0/inspection/arctic_phase017"
out_dir.mkdir(parents=True, exist_ok=True)

rows = []

for run_id in runs:
    log = HOME / "foho_phase0/logs" / f"{run_id}.log"
    text = log.read_text(errors="ignore") if log.exists() else ""

    m = re.findall(
        r"before_frag=([0-9.]+), current_frag=([0-9.]+), margin=([0-9.]+), selected=([A-Za-z0-9_]+)",
        text,
    )

    if m:
        before, after, margin, selected = m[-1]
    else:
        before = after = margin = selected = ""

    bad = bool(re.search(
        r"No such file|FileNotFoundError|CalledProcessError|CUDA out of memory|before_frag=999|referenced before assignment|Traceback|RuntimeError|SyntaxError",
        text,
    ))

    finished = "Finished processing" in text or "Reconstructed object" in text

    rows.append({
        "run_id": run_id,
        "log_exists": log.exists(),
        "finished": finished,
        "bad_pattern": bad,
        "before_frag": before,
        "after_frag": after,
        "selected": selected,
        "log": str(log),
    })

out_csv = out_dir / "arctic_phase017_gpt55_auto_summary.csv"
with out_csv.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

out_md = out_dir / "arctic_phase017_gpt55_auto_summary.md"
with out_md.open("w") as f:
    f.write("# ARCTIC Phase 0.17 GPT-5.5 Auto Selector Summary\n\n")
    f.write("| run_id | finished | bad_pattern | before_frag | after_frag | selected |\n")
    f.write("|---|---:|---:|---:|---:|---|\n")
    for r in rows:
        f.write(
            f"| {r['run_id']} | {r['finished']} | {r['bad_pattern']} | "
            f"{r['before_frag']} | {r['after_frag']} | {r['selected']} |\n"
        )

print("[OK] wrote", out_csv)
print("[OK] wrote", out_md)
print(out_md.read_text())
