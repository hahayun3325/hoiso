from pathlib import Path
import pandas as pd

root = Path("test_splits")
out_dir = Path.home() / "foho_phase0/inspection/eval_scripts"
out_dir.mkdir(parents=True, exist_ok=True)

for name in ["dexycb", "arctic", "oakink"]:
    path = root / f"{name}_test.csv"
    df = pd.read_csv(path)

    # Take a tiny deterministic panel.
    mini = df.head(5).copy()

    out = out_dir / f"{name}_mini5.csv"
    mini.to_csv(out, index=False)

    print(f"\n===== {name} =====")
    print("input:", path)
    print("rows:", len(df))
    print("mini:", out)
    print(mini)
