from pathlib import Path
import pandas as pd
import json

csv_path = Path("docs/phase0/manual_llm_prompts/oakink000_prompt_candidates.csv")
runs_root = Path.home() / "foho_phase0/runs"

df = pd.read_csv(csv_path)

print("run_id,llm,inpaint,hunyuan,final_obj,final_hand,selector,selected")

for _, r in df.iterrows():
    run_id = r["run_id"]
    run = runs_root / run_id

    inpaint = bool(list((run / "ours_inpaint").glob("*inpainted*.png")))
    hunyuan = bool(list((run / "hunyuan_hoi_out").glob("*.ply")))
    final_obj = bool(list((run / "guidance_out").glob("*obj*.ply")))
    final_hand = bool(list((run / "guidance_out").glob("*hand*.ply")))
    report = run / "fallback_out/fallback_report.json"

    selected = ""
    if report.exists():
        try:
            selected = json.loads(report.read_text()).get("selected", "")
        except Exception:
            selected = "parse_error"

    print(
        f"{run_id},{r['llm']},"
        f"{inpaint},{hunyuan},{final_obj},{final_hand},{report.exists()},{selected}"
    )
