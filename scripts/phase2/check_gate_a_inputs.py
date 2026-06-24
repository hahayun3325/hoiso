from pathlib import Path
import pandas as pd

ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon")
manifest = pd.read_csv(ROOT / "gate_a_cases.csv")

ok = True
for _, r in manifest.iterrows():
    for col in ["input_image", "hand_mesh", "object_mesh", "hoi_mesh"]:
        p = Path(r[col])
        exists = p.exists()
        print(f"{r['case']:10s} {col:12s} {exists} {p}")
        ok = ok and exists

print("gate_a_input_preflight_ok =", ok)
if not ok:
    raise SystemExit("[BAD] missing Gate A inputs")
