from pathlib import Path
import pandas as pd
import csv
import os

ROOT = Path("/home/fredcui/Projects/FollowMyHold")
HOME = Path.home()

split = pd.read_csv(ROOT / "test_splits/arctic_test.csv")

cases = ["abox01", "aket01", "ascis01", "alapuse01", "amicuse01"]
rows = []

print("===== split columns =====")
print(list(split.columns))

for case in cases:
    cfg = ROOT / f"configs/generated/pipeline.phase0.arctic_{case}_default.env"
    cfg_text = cfg.read_text(errors="ignore") if cfg.exists() else ""

    image_path = ""
    for line in cfg_text.splitlines():
        if line.startswith("IMAGE_PATH="):
            image_path = line.split("=", 1)[1].strip().strip('"')
            break

    input_name = Path(image_path).name

    # Try multiple matching strategies.
    candidates = split[
        split.astype(str).apply(
            lambda row: any(
                token and token in " ".join(row.values.astype(str))
                for token in [case, input_name, input_name.replace(".jpg", ""), input_name.replace(".png", "")]
            ),
            axis=1,
        )
    ]

    print("\n" + "=" * 80)
    print("case:", case)
    print("image_path:", image_path)
    print("input_name:", input_name)
    print("num_candidates:", len(candidates))

    if len(candidates) > 0:
        print(candidates.head(10).to_string())
        first = candidates.iloc[0].to_dict()
    else:
        first = {}

    row = {
        "case": case,
        "config": str(cfg),
        "image_path": image_path,
        "input_name": input_name,
        "num_split_candidates": len(candidates),
    }
    for k, v in first.items():
        row[f"split_{k}"] = v
    rows.append(row)

out = HOME / "foho_phase0/inspection/arctic_phase017/arctic_phase017_case_to_split_mapping.csv"
out.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(rows).to_csv(out, index=False)
print("\n[OK] wrote", out)
