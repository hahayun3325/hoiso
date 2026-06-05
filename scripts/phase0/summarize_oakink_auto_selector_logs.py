from pathlib import Path
import re
import csv

HOME = Path.home()

runs = [
    ("oakink000_gemini31pro_short", "gemini-3.1-pro"),
    ("oakink000_sonnet46thinking_short", "sonnet-4.6-thinking"),
    ("oakink000_gpt55_short", "gpt-5.5"),
    ("oakink000_gpt55thinking_short", "gpt-5.5-thinking"),
]

out_dir = HOME / "foho_phase0/inspection/oakink_000"
out_dir.mkdir(parents=True, exist_ok=True)
out_csv = out_dir / "oakink000_auto_selector_decision_table.csv"
out_md = out_dir / "oakink000_auto_selector_decision_table.md"

rows = []
for base_id, llm in runs:
    log_path = HOME / "foho_phase0/logs" / f"{base_id}_selector_auto_frag_final.log"
    text = log_path.read_text(errors="ignore") if log_path.exists() else ""

    matches = re.findall(
        r"before_frag=([0-9.]+), current_frag=([0-9.]+), margin=([0-9.]+), selected=([A-Za-z0-9_]+)",
        text,
    )

    if matches:
        before_frag, current_frag, margin, selected = matches[-1]
        status = "OK"
    else:
        before_frag = current_frag = margin = selected = ""
        status = "MISSING_DECISION"

    fallback_bad = bool(re.search(r"before_frag=999|referenced before assignment", text))
    if fallback_bad:
        status = "BAD_FALLBACK"

    rows.append({
        "run_id": base_id,
        "llm": llm,
        "before_frag": before_frag,
        "current_frag": current_frag,
        "selected": selected,
        "status": status,
        "log": str(log_path),
    })

with out_csv.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

with out_md.open("w") as f:
    f.write("# OakInk split000 — Automatic Internal Selector Decisions\n\n")
    f.write("| run_id | llm | before_frag | current_frag | selected | status |\n")
    f.write("|---|---|---:|---:|---|---|\n")
    for r in rows:
        f.write(
            f"| {r['run_id']} | {r['llm']} | {r['before_frag']} | "
            f"{r['current_frag']} | **{r['selected']}** | {r['status']} |\n"
        )

print("[OK] wrote", out_csv)
print("[OK] wrote", out_md)
