from pathlib import Path
import pandas as pd

P = Path.home() / "foho_phase0/inspection/arctic_phase017/paper_style_eval_selected_cases/arctic_selected_cases_dryrun_metrics.csv"
OUT = Path.home() / "foho_phase0/inspection/arctic_phase017/paper_style_eval_selected_cases/arctic_selected_case_hand_side_map.csv"

df = pd.read_csv(P)
ok = df[df["status"] == "ok"].copy()

rows = []
for case, g in ok.groupby("case"):
    sides = sorted(set(g["chosen_gt_hand"].tolist()))
    if len(sides) != 1:
        print("[WARN] method-specific side disagreement:", case, sides)
    rows.append({
        "case": case,
        "chosen_gt_hand": sides[0],
        "methods_seen": ",".join(sorted(g["method"].tolist())),
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

print("[OK] wrote", OUT)
print(out.to_string(index=False))
