from pathlib import Path
import pandas as pd

ROOT = Path("/home/fredcui/Projects/FollowMyHold")
HOME = Path.home()
GT = Path("/home/fredcui/Projects/arctic/unpack/arctic_data/data")

cases = pd.read_csv(ROOT / "docs/phase0/arctic_phase017_selected_cases.csv")

rows = []
for _, r in cases.iterrows():
    case = r["case"]
    default = HOME / "foho_phase0/runs" / f"arctic_{case}_default"
    method = HOME / "foho_phase0/runs" / f"arctic_{case}_gpt55_auto_selector_native_v2"

    row = dict(r)
    row.update({
        "gt_root": str(GT),
        "raw_seq_dir": str(GT / "raw_seqs" / r["subject"] / r["seq_name"]),
        "meta_dir": str(GT / "meta"),
        "object_template_dir": str(GT / "meta/object_vtemplates" / r["object"]),
        "default_hand": str(default / "guidance_out" / f"{case}_hand.ply"),
        "default_obj": str(default / "guidance_out" / f"{case}_obj.ply"),
        "method_hand": str(method / "guidance_out" / f"{case}_hand.ply"),
        "method_obj": str(method / "guidance_out" / f"{case}_obj.ply"),
    })

    for k in ["source_path", "input_path", "default_hand", "default_obj", "method_hand", "method_obj"]:
        row[k + "_exists"] = Path(row[k]).exists()

    rows.append(row)

out = HOME / "foho_phase0/inspection/arctic_phase017/arctic_phase017_paper_eval_manifest.csv"
out.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(rows).to_csv(out, index=False)

print("[OK] wrote", out)
print(pd.DataFrame(rows).to_string(index=False))
