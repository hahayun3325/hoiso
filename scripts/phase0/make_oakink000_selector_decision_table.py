from pathlib import Path
import json
import pandas as pd

csv_path = Path("docs/phase0/manual_llm_prompts/oakink000_prompt_candidates_short.csv")
runs_root = Path.home() / "foho_phase0/runs"
out_csv = Path.home() / "foho_phase0/inspection/oakink_000/oakink000_short_selector_decision_table.csv"
out_md = Path("docs/phase0/oakink000_short_selector_decision_table.md")

df = pd.read_csv(csv_path)
rows = []

for _, r in df.iterrows():
    run_id = r["run_id"]
    report_path = runs_root / run_id / "fallback_out/fallback_report.json"

    selected = "missing"
    initial_frag = ""
    final_frag = ""
    initial_comp = ""
    final_comp = ""

    if report_path.exists():
        rep = json.loads(report_path.read_text())
        selected = rep.get("selected", "")
        scores = rep.get("scores", {})
        if "initial_obj" in scores:
            initial_frag = scores["initial_obj"].get("fragmentation_score", "")
            initial_comp = scores["initial_obj"].get("components", "")
        if "final_obj" in scores:
            final_frag = scores["final_obj"].get("fragmentation_score", "")
            final_comp = scores["final_obj"].get("components", "")

    rows.append({
        "run_id": run_id,
        "llm": r["llm"],
        "selected": selected,
        "initial_components": initial_comp,
        "initial_frag": initial_frag,
        "final_components": final_comp,
        "final_frag": final_frag,
    })

out = pd.DataFrame(rows)
out.to_csv(out_csv, index=False)

with out_md.open("w") as f:
    f.write("# OakInk split000 — Short Prompt Selector Decision Table\n\n")
    f.write(out.to_markdown(index=False))
    f.write("\n")

print("[OK] wrote", out_csv)
print("[OK] wrote", out_md)
print(out)
